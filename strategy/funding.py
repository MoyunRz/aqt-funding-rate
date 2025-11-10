"""
资金费率套利策略

通过合约和现货对冲的方式收取资金费率收益，属于低风险套利策略。

套利原理：
- 正资金费率：合约做空 + 现货做多，收取资金费率
- 负资金费率：合约做多 + 现货做空，收取资金费率
- 价格波动通过对冲抵消，净收益为资金费率

风险提示：市场风险、流动性风险、手续费成本、API风险
"""

from rest.ccxt_client import (
    get_cex_contracts,
    get_cex_spot_candle,
    get_cex_all_position,
    get_cex_fticker,
    get_cex_sticker,
    get_cex_wallet_balance,
    set_cex_margin_leverage,
    set_cex_leverage,
    get_cex_position,
    set_cex_unified_leverage,
    cex_futures_place,
    cex_spot_place,
    cex_futures_close_position,
    find_cex_spot_orders,
    set_cex_dual_mode
)
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

fee = 0.062 / 100.0 * 3
balance = 200
lever = "3"

mp = {}

def watch_filter_funding():
    """筛选高资金费率的合约，返回最优套利机会"""
    logger.info("正在获取合约列表...")
    r = get_cex_contracts()
    if r is None or len(r) == 0:
        logger.warning("无法获取合约列表")
        return
    logger.info(f"获取到 {len(r)} 个合约")
    
    global mp
    flist = []
    
    for v in r:
        if v.name == "MERL_USDT":
            continue
        
        funding_rate = float(v.funding_rate) * 100.0
        
        if funding_rate >= 0.6 or funding_rate <= -0.6:
            print(v.name)
            candle = mp.get(v.name)
            if candle is None:
                sticker = get_cex_spot_candle(v.name, "1m", 1)
                if sticker is None or len(sticker) == 0:
                    time.sleep(1)
                    continue
                mp[v.name] = v
                flist.append(v)
                logger.info(f"{v.name} 资金费率(%): {funding_rate}")
            else:
                flist.append(v)

    def custom_sort_key(item):
        rate = abs(float(item.funding_rate)) * 100.0
        interval = float(24 * 60 * 60) / float(v.funding_interval)
        return rate * interval

    flist.sort(key=custom_sort_key, reverse=True)
    
    if len(flist) == 0:
        return
    
    return flist[0]


def watch_history_funding():
    """监控并执行资金费率套利策略"""
    fps = get_cex_all_position()
    if fps is not None and len(fps) > 0:
        logger.warning("已经存在仓位信息，跳过本次")
        return

    item = watch_filter_funding()
    if item is None:
        return
    
    current_timestamp = int(time.time())
    time_in_interval = current_timestamp % item.funding_interval
    
    if time_in_interval > (item.funding_interval - 10):
        fticker = get_cex_fticker(item.name)
        if fticker is None or len(fticker) == 0:
            logger.warning(f"无法获取 {item.name} 的合约行情数据")
            time.sleep(1)
            return
        
        sticker = get_cex_sticker(item.name)
        if sticker is None or len(sticker) == 0:
            logger.warning(f"无法获取 {item.name} 的现货行情数据")
            time.sleep(1)
            return
        
        f_ask = fticker[0].lowest_ask
        f_bid = fticker[0].highest_bid
        s_ask = sticker[0].lowest_ask
        
        wallet = get_cex_wallet_balance()
        if wallet is None:
            logger.warning("无法获取钱包余额")
            return
        
        wallet_margin = wallet.details["spot"]
        spot_amount = float(wallet_margin.amount)
        
        if spot_amount >= balance * 2:
            set_cex_margin_leverage(item.name, lever)
            set_cex_leverage(item.name, lever)
            
            funding_rate = float(item.funding_rate) * 100.0
            if funding_rate > 0:
                size = int(float(balance) / float(f_bid))
                csz = 1.0 / float(item.quanto_multiplier) * size
                
                if csz < 1:
                    return
                
                size = float(s_ask) * size * 1.01
                open_order(item.name, size, int(-csz))
            else:
                size = int(float(balance) / float(f_ask))
                csz = 1.0 / float(item.quanto_multiplier) * size
                
                if csz < 1:
                    return
                open_order(item.name, size, int(csz))


def open_order(name: str, size: float, csz: int):
    """执行对冲开仓：同时开启合约和现货仓位"""
    psList = get_cex_position(name)
    if psList is not None and psList.size != 0:
        logger.warning(f"{name} 已经有持仓")
        return

    name_list = name.split("_")
    set_cex_unified_leverage(name_list[0], lever)
    set_cex_leverage(name, lever)
    
    if csz > 0:
        res = cex_futures_place(name, "0", csz)
        if res is None:
            logger.error(f"合约下单失败: {name}")
            return

        if res.id != "":
            res1 = cex_spot_place(name, "sell", str(size))
            if res1 is None or res1 == "":
                logger.error("现货开空失败")
                cex_futures_close_position(name)
                return
            time.sleep(30)
    else:
        res = cex_futures_place(name, "0", csz)
        if res is None:
            logger.error(f"合约下单失败: {name}")
            return

        if res.id != "":
            res1 = cex_spot_place(name, "buy", str(size))
            if res1 is None or res1 == "":
                logger.error("现货开多失败")
                cex_futures_close_position(name)
                return
            time.sleep(30)

def watch_position():
    """监控持仓并在盈利时自动平仓"""
    fps = get_cex_all_position()
    if fps is None:
        logger.warning("无法获取仓位信息")
        return
    
    for i, v in enumerate(fps):
        pnl = float(v.unrealised_pnl) + float(v.realised_pnl)
        
        spot_order_list = find_cex_spot_orders(v.contract)
        if spot_order_list is None or len(spot_order_list) == 0:
            logger.warning(f"无法获取 {v.contract} 的现货订单")
            continue
        
        spot_order_list.sort(key=lambda x: x.update_time_ms, reverse=True)
        
        fee = float(spot_order_list[0].fee) * 3
        spnl = fee
        amount = float(spot_order_list[0].amount)
        
        sticker = get_cex_sticker(v.contract)
        if sticker is None or len(sticker) == 0:
            logger.warning(f"无法获取 {v.contract} 的现货行情")
            time.sleep(1)
            continue

        if spot_order_list[0].status != "closed":
            logger.warning(f"请手动处理 {v.contract} 仓位，订单状态未关闭")
            continue
        
        sz = 0.0
        if spot_order_list[0].status == "closed":
            price = float(spot_order_list[0].avg_deal_price)
            
            if spot_order_list[0].side == "sell" and v.size > 0:
                sz = amount
                spnl = -(float(sticker[0].highest_bid) - price) * amount + fee
                
            if spot_order_list[0].side == "buy" and v.size < 0:
                sz = float(amount / price)
                spnl = fee + (float(sticker[0].lowest_ask) - price) * sz

        side = "long"
        if v.size < 0:
            side = "short"
        
        logger.info(f"交易对 {v.contract}: 合约{side} {v.size} 收益{pnl}, 现货{spot_order_list[0].side} {sz} 收益{spnl}, 总收益{pnl + spnl}")
        
        if pnl + spnl > 0:
            logger.info(f"平仓交易对：{v.contract} 总收益：{pnl + spnl}")
            cex_futures_close_position(v.contract)
            
            if side == "long":
                cex_spot_place(v.contract, "buy", str(float(sticker[0].lowest_ask) * sz))
            if side == "short":
                cex_spot_place(v.contract, "sell", str(amount))

def run_funding():
    """资金费率套利策略主函数"""
    try:
        logger.info("正在初始化策略...")
        set_cex_dual_mode(False)
        logger.info("持仓模式设置完成")
        
        logger.info("=" * 60)
        logger.info("资金费率套利策略启动，开始监控市场...")
        logger.info("=" * 60)
        while True:
            watch_history_funding()
            watch_position()
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出现异常: {e}")

