import rest
import time
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

fee = 0.062 / 100.0 * 3
balance = 200
lever = "2"

def watch_history_funding():
    """
    根据资金费率进行套利
    :return:
    """
    r = rest.get_cex_contracts()
    if r is None:
        logger.warning("无法获取合约列表")
        return
        
    for v in r:
        funding_rate = float(v.funding_rate) * 100.0
        if funding_rate > 0.01 or funding_rate < -0.01:
            logger.info(f"{v.name} 资金费率(%): {funding_rate}")
            # 判断现在是不是快到了下次费率结算时间点
            # 获取当前的时间戳
            current_timestamp = int(time.time())
            # print(f"当前时间戳: {current_timestamp}")
            # if current_timestamp % v.funding_interval > (v.funding_interval-10):
            if True:
                fticker = rest.get_cex_fticker(v.name)
                if fticker is None or len(fticker) == 0:
                    logger.warning(f"无法获取 {v.name} 的期货行情数据")
                    time.sleep(1)
                    continue
                    
                # 最新卖方最低价
                f_lowest_ask = fticker[0].lowest_ask

                wallet = rest.get_cex_wallet_balance()
                if wallet is None:
                    logger.warning("无法获取钱包余额")
                    continue

                # wallet_futures = wallet.details["futures"]
                wallet_margin = wallet.details["spot"]

                # futures_amount = float(wallet_futures.amount)
                spot_amount = float(wallet_margin.amount)
                if spot_amount >= balance * 2:
                    # 设置杠杠
                    rest.set_cex_margin_leverage(v.name, lever)
                    rest.set_cex_leverage(v.name, lever)
                    # 根据合约的乘数 计算 张数 币数量

                    size = int(float(balance) / float(f_lowest_ask))
                    csz = 1.0 / float(v.quanto_multiplier) * size
                    if csz < 1:
                        continue
                    if funding_rate > 0:
                        # 如果是正数费
                        # 合约需要做空 看买盘
                        # 现货需要做多 看卖盘
                        open_order(v.name, size, int(-csz))
                    else:
                        # 如果是负数费率
                        # 合约需要做多 看卖盘
                        # 现货需要做空 看买盘
                        open_order(v.name, size, int(csz))

def open_order(name: str, size: int, csz: int):
    """
    开仓: 现货杠杆 + 合约
    :param name: 合约名字
    :param size: 数量
    :return: none
    """
    # 先获取现货的最高杠杆倍数
    # 切割
    name_list = name.split("_")
    resp = rest.get_cex_unified_leverage(name_list[0])
    # 最高杠杆倍数
    if resp is None or len(resp) < 2:
        logger.warning(f"无法获取 {name_list[0]} 的统一杠杆配置")
        return
        
    max_leverage = resp[0].max_leverage
    # 设置现货借贷币种杠杆倍数
    rest.set_cex_unified_leverage(name_list[0], max_leverage)
    # 设置合约杠杆倍数
    rest.set_cex_leverage(name, max_leverage)
    # 对该币种下单
    if size > 0:
        # 现货做空
        res = rest.cex_futures_place(name, "0", csz)
        if res is None:
            logger.error(f"期货下单失败: {name}")
            return
            
        if res.id != "":
            res1 = rest.cex_spot_place(name, "sell", "0", str(size))
            if res1 is None:
                logger.error("现货开空失败")
                rest.cex_futures_close_position(name)
                return
            if res1 == "":
                logger.error("合约开空失败")
                rest.cex_futures_close_position(name)
                return
    else:
        # 现货做多
        res = rest.cex_spot_place(name, "buy", "0", str(size))
        if res is None:
            logger.error(f"现货下单失败: {name}")
            return
            
        if res.id != "":
            res1 = rest.cex_futures_place(name, "0", csz)
            if res1 is None:
                logger.error("现货开多失败")
                rest.cex_futures_close_position(name)
                return
            if res1 == "":
                logger.error("现货开多失败")
                rest.cex_futures_close_position(name)
                return

def watch_position():
    fps = rest.get_cex_all_position()
    if fps is None:
        logger.warning("无法获取仓位信息")
        return
        
    for i, v in enumerate(fps):
        # 计算持仓收益：浮动收益+已经收取
        pnl = float(v.unrealised_pnl) + float(v.realised_pnl)
        spot_order_list = rest.find_cex_spot_orders(v.contract)
        if spot_order_list is None:
            logger.warning(f"无法获取 {v.contract} 的现货订单")
            continue
            
        if len(spot_order_list) == 0:
            logger.warning(f"未找到 {v.contract} 的现货订单")
            continue
            
        fee = float(spot_order_list[0].fee) * 3
        spnl = fee
        amount = float(spot_order_list[0].amount)
        if spot_order_list[0].status != "closed":
            logger.warning(f"请手动处理 {v.contract} 仓位，订单状态未关闭")
            continue
            
        if spot_order_list[0].status == "closed":
            # 计算收益
            sticker = rest.get_cex_sticker(v.contract)
            if sticker is None or len(sticker) == 0:
                logger.warning(f"无法获取 {v.contract} 的现货行情")
                time.sleep(1)
                continue
                
            price = float(spot_order_list[0].price)

            if spot_order_list[0].side == "sell" and v.size > 0:
                # 做空 highest_bid 现在的买价
                spnl = -(float(sticker[0].highest_bid) - price) * amount + fee
            if spot_order_list[0].side == "buy" and v.size < 0:
                # 做多  lowest_ask 现在的买出价
                spnl = fee + (float(sticker[0].lowest_ask) - price) * float(spot_order_list[0].amount)

        side = "long"
        if v.size < 0:
            side = "short"
            
        logger.info(f"==================== 交易对 {v.contract} ====================")
        logger.info(f"合约方向：{side} 持仓收益：{pnl}")
        logger.info(f"现货方向：{spot_order_list[0].side} 持仓收益：{spnl}")
        logger.info(f"预计总收益：{pnl + spnl}")
        
        if pnl > 0:
            logger.info(f"平仓交易对：{v.contract} 总收益：{pnl + spnl}")
            rest.cex_futures_close_position(v.contract)
            if side == "long":
                rest.cex_spot_place(v.contract, "buy", "0", str(amount))
            if side == "short":
                rest.cex_spot_place(v.contract, "sell", "0", str(amount))

def run_funding():
    try:
        rest.set_cex_dual_mode(False)
        # 循环判断最高资金费率的合约
        while True:
            watch_history_funding()
            watch_position()
            time.sleep(3)
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出现异常: {e}")

if __name__ == "__main__":
    # 运行其中一个函数
    run_funding()