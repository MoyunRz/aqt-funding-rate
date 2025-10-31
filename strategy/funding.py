import rest
import time
from  gate_api import Position
import asyncio
list_ps = []
env =1

def mock_all_position():
    global list_ps
    for i, ps in enumerate(list_ps):
        kline = rest.get_cex_candle(ps.contract, "3m", 3)
        # 根据市场价格计算收益率
        # 计算浮动收益
        mpx = float(kline[0].c)
        entry_price = float( ps.entry_price)
        ps.unrealised_pnl = str((mpx -entry_price) * ps.size)
        list_ps[i] = ps
    return list_ps

def mock_watch_position():
    global list_ps
    indices_to_remove = []
    positions = mock_all_position()
    for i, v in enumerate(positions):
        print(i,v.contract, v.size, v.entry_price, v.leverage)
        # 计算持仓收益：浮动收益+已经收取
        pnl = float(v.unrealised_pnl) + float(v.realised_pnl)
        print("持仓收益：", pnl)
        if pnl > 0:
            print("平仓")
            # 删除该下标
            indices_to_remove.append(i)

    for i in sorted(indices_to_remove, reverse=True):
        del list_ps[i]

def get_history_funding():
    """
    根据资金费率进行套利
    :return:
    """
    global list_ps
    r = rest.get_cex_contracts()

    for v in r:
        funding_rate = float(v.funding_rate) * 100.0
        if funding_rate > 0.3 or funding_rate < -0.3:
            print(v.name, funding_rate)
            # 判断现在是不是快到了下次费率结算时间点
            # 获取当前的时间戳
            current_timestamp = int(time.time())
            # print(f"当前时间戳: {current_timestamp}")
            if (current_timestamp%v.funding_interval <10) or env ==1:
                # print("快到了 查询k线数据")
                # 查询k线数据
                kline = rest.get_cex_candle(v.name,"3m", 10)
                # print(kline)
                mpx = float(kline[0].c)
                if funding_rate > 0:
                    # 如果是正数费率需要做空
                    print("做空")
                    mock_open_order(v.name,funding_rate, mpx, -1000, kline)
                else:
                    # 如果是负数费率需要做多
                    print("做多")
                    mock_open_order(v.name,funding_rate, mpx, 1000, kline)


def mock_open_order(name:str,funding_rate:float,px:float,size:int,kline):
    """
    模拟开仓
    :param funding_rate:
    :param name: 合约名字
    :param px: 价格
    :param size: 数量
    :param kline: K线数据
    :return: none
    """
    if funding_rate <0:
        funding_rate = -funding_rate
    ps = Position(
        contract=name,
        entry_price=str(px),
        size=size,
        leverage="10",
        realised_pnl= "0", # 实现收益
    )
    isHave = False
    for i, ps1 in enumerate(list_ps):
        entry_price = float(ps1.entry_price)
        if ps1.contract == ps.contract and ps1.size < 0:
            sz = -size
            vol = (entry_price * (-ps1.size) + px * sz)
            ps1.entry_price = vol / (-ps1.size + sz)
            ps1.size = ps1.size - sz
            ps1.realised_pnl = float(ps1.realised_pnl) + funding_rate * vol / 100.0
            list_ps[i] = ps1
            isHave = True
        if ps1.contract == ps.contract and ps1.size > 0 and size>0:
            vol = (entry_price * ps1.size + px * size)
            ps1.entry_price = vol / (ps1.size + size)
            ps1.size = ps1.size + size
            ps1.realised_pnl = float(ps1.realised_pnl) + funding_rate * vol / 100.0
            list_ps[i] = ps1
            isHave = True
    if not isHave:
        realised_pnl = px * size * funding_rate
        ps.realised_pnl = str(realised_pnl)
        if size < 0:
            ps.realised_pnl = str(-realised_pnl)
        list_ps.append(ps)


def run_funding():
    # 循环判断最高资金费率的合约
    while True:
        get_history_funding()
        mock_watch_position()
        for i, ps in enumerate(list_ps):
            print(ps.contract, ps.size, ps.entry_price, ps.leverage)
        time.sleep(1)

if __name__ == "__main__":
    # 运行其中一个函数
    run_funding()
