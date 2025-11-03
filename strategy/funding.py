import rest
import time
from gate_api import Position

fee = 0.062 / 100.0 * 3
list_futures_ps = {}
list_spot_ps = {}
env = 1


def get_history_funding():
    """
    根据资金费率进行套利
    :return:
    """
    global list_futures_ps
    r = rest.get_cex_contracts()
    if r is None:
        return

    for v in r:
        funding_rate = float(v.funding_rate) * 100.0
        if funding_rate > 0.6 or funding_rate < -0.6:
            print(v.name, "资金费率(%):", funding_rate)
            # 判断现在是不是快到了下次费率结算时间点
            # 获取当前的时间戳
            current_timestamp = int(time.time())
            # print(f"当前时间戳: {current_timestamp}")
            if (current_timestamp % v.funding_interval < 10) or env == 1:

                fticker = rest.get_cex_fticker(v.name)
                if fticker is None or len(fticker) == 0:
                    time.sleep(1)
                    continue
                sticker = rest.get_cex_sticker(v.name)
                if sticker is None or len(sticker) == 0:
                    time.sleep(1)
                    continue
                # 最新卖方最低价
                f_lowest_ask = fticker[0].lowest_ask
                # 最新买方最高价
                f_highest_bid = fticker[0].highest_bid

                s_lowest_ask = sticker[0].lowest_ask
                s_highest_bid = sticker[0].highest_bid
                if funding_rate > 0:
                    # 如果是正数费
                    # 合约需要做空 看买盘
                    # 现货需要做多 看卖盘
                    mock_open_order(v.name, funding_rate, float(f_highest_bid), float(s_lowest_ask), -3000)
                else:
                    # 如果是负数费率
                    # 合约需要做多 看卖盘
                    # 现货需要做空 看买盘
                    mock_open_order(v.name, funding_rate, float(f_lowest_ask), float(s_highest_bid), 3000)


def open_order(name: str, funding_rate: float, mpx: float, size: int):
    """
    开仓: 现货杠杆 + 合约
    :param funding_rate:
    :param name: 合约名字
    :param mpx: 价格
    :param size: 数量
    :return: none
    """
    # 先获取现货的最高杠杆倍数
    # 切割
    name_list = name.split("_")
    resp = rest.get_cex_unified_leverage(name_list[0])
    # 最高杠杆倍数
    max_leverage = resp.max_leverage
    # 设置现货借贷币种杠杆倍数
    rest.set_cex_unified_leverage(name_list[0], max_leverage)
    # 设置合约杠杆倍数
    rest.set_cex_leverage(name, max_leverage)
    # 对该币种下单
    if size > 0:
        # 现货做空
        rest.cex_spot_place(name, "sell", str(mpx), str(size))
        rest.cex_futures_place(name, "0", size)
    else:
        # 现货做多
        rest.cex_spot_place(name, "buy", str(mpx), str(size))
        rest.cex_futures_place(name, "0", size)


def mock_open_order(name: str, funding_rate: float, fpx: float, spx: float, size: int):
    """
    模拟开仓
    :param funding_rate:
    :param name: 合约名字
    :param fpx: 合约价格
    :param spx: 现货价格
    :param size: 数量
    :return: none
    """

    print(name, "合约价格:", fpx, "现货价格:", spx)
    global list_futures_ps, list_spot_ps

    if funding_rate < 0:
        funding_rate = -funding_rate

    funding_rate = funding_rate / 100.0
    fps = Position(
        contract=name,
        entry_price=str(fpx),
        size=size,
        leverage="10",
        realised_pnl="0",  # 实现收益
    )
    sps = Position(
        contract=name,
        entry_price=str(spx),
        size=-size,
        leverage="10",
        realised_pnl="0",  # 实现收益
    )

    isHave = False
    ps1 = list_futures_ps.get(name)
    ps2 = list_spot_ps.get(name)
    if ps1 is not None:
        fprice = float(ps1.entry_price)
        sprice = float(ps2.entry_price)
        if ps1.contract == fps.contract and ps1.size < 0:
            sz = -size
            fvol = (fprice * (-ps1.size) + fpx * sz)
            ps1.entry_price = fvol / (-ps1.size + sz)
            ps1.size = ps1.size + size
            ps1.realised_pnl = float(ps1.realised_pnl) + (funding_rate - fee) * fvol
            list_futures_ps[name] = ps1

            svol = (sprice * ps2.size + spx * sz)
            ps2.entry_price = svol / (ps2.size + sz)
            ps2.size = ps2.size + sz
            ps2.realised_pnl = float(ps2.realised_pnl) - svol * fee
            list_spot_ps[name] = ps2

            isHave = True

        if ps1.contract == fps.contract and ps1.size > 0 and size > 0:
            # ----------------- 合约 --------------------
            fvol = (fprice * ps1.size + fpx * size)
            ps1.entry_price = fvol / (ps1.size + size)
            # 做空
            ps1.size = ps1.size + size
            ps1.realised_pnl = float(ps1.realised_pnl) + (funding_rate - fee) * fvol
            list_futures_ps[name] = ps1

            # ----------------- 现货 --------------------
            svol = (sprice * (-ps2.size) + spx * size)
            ps2.entry_price = svol / (-ps2.size + size)
            ps2.size = ps2.size - size
            ps2.realised_pnl = float(ps2.realised_pnl) - svol * fee
            list_spot_ps[name] = ps2
            isHave = True

    if not isHave:
        ffee = fpx * size * fee
        sfee = spx * size * fee
        realised_pnl = fpx * size * funding_rate
        fps.realised_pnl = str(realised_pnl)
        if size < 0:
            # 正数收益
            fps.realised_pnl = str(-realised_pnl + ffee)
            sps.realised_pnl = str(sfee)

        if size > 0:
            # 正数收益
            fps.realised_pnl = str(realised_pnl - ffee)
            sps.realised_pnl = str(-sfee)

        print("----------------------------------------- 开仓 -----------------------------------------------")
        print(fps.contract, "合约价格:", fpx, "合约数量:", fps.size, "合约手续费:", ffee, "合约实现收益:",
              fps.realised_pnl)
        print(fps.contract, "现货价格:", spx, "合约数量:", sps.size, "现货手续费:", sfee, "现货实现收益:",
              sps.realised_pnl)
        print("预计套利收益:", float(fps.realised_pnl) + float(sps.realised_pnl))
        print("---------------------------------------------------------------------------------------------")

        list_futures_ps[name] = fps
        list_spot_ps[name] = sps


def mock_all_futures_position():
    global list_futures_ps

    for i, key in enumerate(list_futures_ps):
        fticker = rest.get_cex_fticker(key)
        if fticker is None or len(fticker) == 0:
            time.sleep(1)
            continue
        # 最新卖方最低价
        f_lowest_ask = float(fticker[0].lowest_ask)
        # 最新买方最高价
        f_highest_bid = float(fticker[0].highest_bid)
        # 根据市场价格计算收益率
        # 计算浮动收益
        ps = list_futures_ps.get(key)
        mpx = f_lowest_ask
        if ps.size > 0:
            mpx = f_highest_bid
        entry_price = float(ps.entry_price)
        ps.unrealised_pnl = str((mpx - entry_price) * ps.size)
        list_futures_ps[key] = ps
    return list_futures_ps


def mock_all_spot_position():
    global list_spot_ps
    for i, key in enumerate(list_spot_ps):
        # 根据市场价格计算收益率
        # 计算浮动收益
        ps = list_spot_ps.get(key)
        sticker = rest.get_cex_sticker(key)
        if sticker is None or len(sticker) == 0:
            time.sleep(1)
            continue
        s_lowest_ask = float(sticker[0].lowest_ask)
        s_highest_bid = float(sticker[0].highest_bid)
        # 假设做空，平仓需要看卖盘
        mpx = s_lowest_ask
        if ps.size > 0:
            # 我要卖出，需要看买盘
            mpx = s_highest_bid
        print(key, "现在的价格", mpx)
        entry_price = float(ps.entry_price)
        ps.unrealised_pnl = str((mpx - entry_price) * ps.size)
        list_spot_ps[key] = ps
    return list_spot_ps


def mock_watch_position():
    global list_futures_ps
    global list_spot_ps
    key_list = []
    fps = mock_all_futures_position()
    sps = mock_all_spot_position()

    for key in fps:
        v = fps[key]
        # 计算持仓收益：浮动收益+已经收取
        pnl = float(v.unrealised_pnl) + float(v.realised_pnl)
        v1 = sps.get(key)
        spnl = float(v1.unrealised_pnl) + float(v1.realised_pnl)
        side = "long"
        if v.size < 0:
            side = "short"

        sside = "short"
        if v.size < 0:
            sside = "long"

        print("==================== 交易对 ", key, "====================")
        print("合约方向：", side, " 持仓收益：", pnl)
        print("现货方向：", sside, " 持仓收益：", spnl)
        print("预计总收益：", pnl + spnl)

        if pnl > 0:
            print("平仓交易对：", key, "总收益：", pnl + spnl)
            key_list.append(key)

    for key in key_list:
        del list_futures_ps[key]
        del list_spot_ps[key]


def run_funding():
    # 循环判断最高资金费率的合约
    while True:
        get_history_funding()
        time.sleep(5)
        mock_watch_position()
        time.sleep(1)


if __name__ == "__main__":
    # 运行其中一个函数
    run_funding()
