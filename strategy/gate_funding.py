"""
资金费率套利策略 (Funding Rate Arbitrage Strategy)

============================================================
策略概述
============================================================
本策略通过合约和现货对冲的方式，收取资金费率收益，属于低风险套利策略。

资金费率机制：
- 永续合约通过资金费率机制锚定现货价格
- 当合约价格 > 现货价格时，资金费率为正，多头付费给空头
- 当合约价格 < 现货价格时，资金费率为负，空头付费给多头
- 资金费率通常每8小时结算一次

============================================================
套利原理
============================================================
通过同时持有相反方向的合约和现货头寸，实现价格对冲：

1. 正资金费率套利（多头付空头）：
   - 合约：做空（收取资金费率）
   - 现货：做多（借U买币）
   - 价格涨：合约亏、现货赚，互相抵消
   - 价格跌：合约赚、现货亏，互相抵消
   - 净收益：资金费率收入

2. 负资金费率套利（空头付多头）：
   - 合约：做多（收取资金费率）
   - 现货：做空（借币卖出）
   - 价格波动：同样实现对冲
   - 净收益：资金费率收入

============================================================
策略优势
============================================================
✅ 低风险：合约和现货对冲，不承担价格波动风险
✅ 稳定收益：只赚取资金费率，收益可预测
✅ 自动化：自动扫描、开仓、平仓
✅ 高效率：每秒扫描，不错过机会

============================================================
风险提示
============================================================
⚠️ 市场风险：极端行情下可能出现滑点
⚠️ 流动性风险：部分币种流动性不足，难以成交
⚠️ 手续费：频繁交易会产生手续费，需要覆盖成本
⚠️ API风险：交易所API延迟或故障可能导致对冲失败

============================================================
作者信息
============================================================
策略类型：资金费率套利
适用交易所：Gate.io
适用市场：永续合约 + 现货杠杆
风险等级：低
"""

import rest
import time
import logging

# ==================== 配置日志记录 ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== 全局配置参数 ====================
# 交易费率：0.062% * 3（包括开仓、平仓和现货交易费用）
fee = 0.062 / 100.0 * 3
# 每次交易的余额（单边）
balance = 200
# 杠杆倍数
lever = "3"

# ==================== 全局缓存 ====================
# 用于缓存已经检测过的合约信息，避免重复API调用
mp = {}

def watch_filter_funding():
    """
    筛选高资金费率的合约
    
    功能说明：
    1. 获取所有可用的合约列表
    2. 筛选资金费率绝对值 > 0.3% 的合约
    3. 按照"资金费率绝对值 × 每日结算次数"排序
    4. 返回最优的套利机会
    
    Returns:
        Contract: 资金费率最高的合约对象，如果没有符合条件的返回 None
    """
    # 获取所有CEX合约列表
    r = rest.get_cex_contracts()
    if r is None:
        logger.warning("无法获取合约列表")
        return
    
    # 使用全局缓存字典
    global mp
    flist = []  # 符合条件的合约列表
    
    # 遍历所有合约，筛选高资金费率的合约
    for v in r:
        if v.name == "MERL_USDT":
            continue
        # 将资金费率转换为百分比
        funding_rate = float(v.funding_rate) * 100.0
        
        # 只关注资金费率绝对值 > 0.3% 的合约（套利空间大）
        if funding_rate >= 0.6 or funding_rate <= -0.6:
            print(v.name)
            # 检查是否已经在缓存中
            candle = mp.get(v.name)
            if candle is None:
                # 首次发现该合约，获取K线数据验证该交易对是否可用
                sticker = rest.get_cex_spot_candle(v.name,"1m",1)
                if sticker is None or len(sticker) == 0:
                    time.sleep(1)
                    continue
                # 加入缓存
                mp[v.name] = v
                flist.append(v)
                logger.info(f"{v.name} 资金费率(%): {funding_rate}")
            else:
                # 已在缓存中，直接添加
                flist.append(v)

    # 自定义排序规则：按照年化收益率排序
    def custom_sort_key(item):
        """
        计算合约的套利优先级
        
        公式：资金费率绝对值 × 每日结算次数
        - 资金费率越高，套利空间越大
        - 结算次数越多，收益累积越快
        """
        rate = abs(float(item.funding_rate)) * 100.0
        # 计算每日结算次数 = 24小时秒数 / 结算间隔秒数
        interval = float(24 * 60 * 60) / float(v.funding_interval)
        return rate * interval

    # 使用自定义排序规则对过滤后的列表进行排序（降序）
    flist.sort(key=custom_sort_key, reverse=True)
    
    # 如果没有符合条件的合约，返回 None
    if len(flist) == 0:
        # logger.warning("没有合适的合约")
        return
    
    # 返回资金费率最高（套利价值最大）的合约
    return flist[0]


def watch_history_funding():
    """
    监控并执行资金费率套利策略
    
    策略原理：
    - 当资金费率为正（多头付空头）：合约做空 + 现货做多，收取资金费
    - 当资金费率为负（空头付多头）：合约做多 + 现货做空，收取资金费
    
    触发条件：
    - 没有持仓
    - 找到符合条件的高资金费率合约
    - 距离下次结算时间 < 10秒（在结算前开仓）
    - 钱包余额充足
    
    Returns:
        None
    """
    # ==================== 第1步：检查是否已有持仓 ====================
    # 如果已经有持仓，则跳过本次，避免重复开仓
    fps = rest.get_cex_all_position()
    if fps is not None and len(fps) > 0:
        logger.warning("已经存在仓位信息，跳过本次")
        return

    # ==================== 第2步：获取最优套利合约 ====================
    item = watch_filter_funding()
    if item is None:
        # logger.warning("没有合适的合约")
        return
    
    # ==================== 第3步：判断是否接近结算时间 ====================
    # 策略：在资金费率结算前10秒内开仓，结算后立即平仓，快速套利
    current_timestamp = int(time.time())
    # 计算当前在结算周期中的位置
    time_in_interval = current_timestamp % item.funding_interval
    # 如果距离下次结算不到10秒，执行开仓
    if time_in_interval > (item.funding_interval - 10):
        # ==================== 第4步：获取市场行情数据 ====================
        # 获取合约行情
        fticker = rest.get_cex_fticker(item.name)
        if fticker is None or len(fticker) == 0:
            logger.warning(f"无法获取 {item.name} 的合约行情数据")
            time.sleep(1)
            return
        
        # 获取现货行情
        sticker = rest.get_cex_sticker(item.name)
        if sticker is None or len(sticker) == 0:
            logger.warning(f"无法获取 {item.name} 的现货行情数据")
            time.sleep(1)
            return
        
        # 提取关键价格信息
        f_ask = fticker[0].lowest_ask   # 合约卖一价（做多用）
        f_bid = fticker[0].highest_bid  # 合约买一价（做空用）
        s_ask = sticker[0].lowest_ask   # 现货卖一价（买入用）
        
        # ==================== 第5步：检查钱包余额 ====================
        wallet = rest.get_cex_wallet_balance()
        if wallet is None:
            logger.warning("无法获取钱包余额")
            return
        
        # 获取现货账户余额
        wallet_margin = wallet.details["spot"]
        spot_amount = float(wallet_margin.amount)
        
        # 判断余额是否充足（需要 balance * 2，因为现货和合约各需要 balance）
        if spot_amount >= balance * 2:
            # ==================== 第6步：设置杠杆倍数 ====================
            # 设置现货杠杆（用于借币做空）
            rest.set_cex_margin_leverage(item.name, lever)
            # 设置合约杠杆
            rest.set_cex_leverage(item.name, lever)
            
            # ==================== 第7步：计算开仓数量并执行 ====================
            # 根据资金费率正负，采取不同的套利策略
            funding_rate = float(item.funding_rate) * 100.0  # 转换为百分比
            if funding_rate > 0:
                # ========== 正资金费率策略 ==========
                # 多头付费给空头，我们收费：合约做空 + 现货做多
                
                # 计算现货数量（币本位）
                size = int(float(balance) / float(f_bid))
                # 计算合约张数（根据合约乘数转换）
                csz = 1.0 / float(item.quanto_multiplier) * size
                
                # 张数必须 >= 1
                if csz < 1:
                    return
                
                # 计算现货买入金额（价格 * 数量 * 1.01，留1%余量）
                size = float(s_ask) * size * 1.01
                # 执行开仓：合约做空（负数表示空头）+ 现货做多
                open_order(item.name, size, int(-csz))
            else:
                # ========== 负资金费率策略 ==========
                # 空头付费给多头，我们收费：合约做多 + 现货做空
                
                # 计算现货数量（币本位）
                size = int(float(balance) / float(f_ask))
                # 计算合约张数
                csz = 1.0 / float(item.quanto_multiplier) * size
                
                # 张数必须 >= 1
                if csz < 1:
                    return
                # 执行开仓：合约做多（正数表示多头）+ 现货做空
                open_order(item.name, size, int(csz))


def open_order(name: str, size: float, csz: int):
    """
    执行对冲开仓：同时开启合约和现货仓位
    
    对冲原理：
    - 合约和现货方向相反，价格涨跌互相抵消
    - 只赚取资金费率，不承担价格波动风险
    
    Args:
        name (str): 合约名称，如 "BTC_USDT"
        size (float): 现货交易金额（USDT）
        csz (int): 合约张数（正数=做多，负数=做空）
    
    Returns:
        None
    """
    # ==================== 第1步：检查是否已有持仓 ====================
    # 避免重复开仓，防止仓位叠加
    psList = rest.get_cex_position(name)
    if psList is not None and psList.size!=0:
        logger.warning(f"{name} 已经有持仓")
        return

    # ==================== 第2步：提取币种名称 ====================
    # 从 "BTC_USDT" 中提取 "BTC"
    name_list = name.split("_")

    # ==================== 第3步：配置杠杆倍数 ====================
    # 设置现货杠杆（用于借币做空或借U做多）
    rest.set_cex_unified_leverage(name_list[0], lever)
    # 设置合约杠杆
    rest.set_cex_leverage(name, lever)
    
    # ==================== 第4步：执行对冲开仓 ====================
    if csz > 0:
        # ========== 策略A：合约做多 + 现货做空 ==========
        # 适用于负资金费率（空头付费给多头）
        
        # 第一步：开合约多单
        res = rest.cex_futures_place(name, "0", csz)
        if res is None:
            logger.error(f"合约下单失败: {name}")
            return

        # 第二步：开现货空单（借币卖出）
        if res.id != "":
            res1 = rest.cex_spot_place(name, "sell", str(size))
            if res1 is None or res1 == "":
                logger.error("现货开空失败")
                # 回滚：关闭已开的合约仓位
                rest.cex_futures_close_position(name)
                return
            # 等待30秒，确保订单完全成交
            time.sleep(30)
    else:
        # ========== 策略B：合约做空 + 现货做多 ==========
        # 适用于正资金费率（多头付费给空头）
        
        # 第一步：开合约空单
        res = rest.cex_futures_place(name, "0", csz)
        if res is None:
            logger.error(f"合约下单失败: {name}")
            return

        # 第二步：开现货多单（买入）
        if res.id != "":
            res1 = rest.cex_spot_place(name, "buy",  str(size))
            if res1 is None or res1 == "":
                logger.error("现货开多失败")
                # 回滚：关闭已开的合约仓位
                rest.cex_futures_close_position(name)
                return
            # 等待30秒，确保订单完全成交
            time.sleep(30)

def watch_position():
    """
    监控持仓并在盈利时自动平仓
    
    功能说明：
    1. 获取所有合约持仓
    2. 查找对应的现货订单
    3. 计算总收益（合约收益 + 现货收益 - 手续费）
    4. 如果总收益 > 0，自动平仓
    
    收益计算：
    - 合约收益 = 未实现盈亏 + 已实现盈亏（包含资金费率）
    - 现货收益 = (当前价格 - 开仓价格) × 持仓数量 - 手续费
    - 总收益 = 合约收益 + 现货收益
    
    Returns:
        None
    """
    # ==================== 第1步：获取所有持仓 ====================
    fps = rest.get_cex_all_position()
    if fps is None:
        logger.warning("无法获取仓位信息")
        return
    
    # ==================== 第2步：遍历每个持仓 ====================
    for i, v in enumerate(fps):
        # ==================== 第3步：计算合约收益 ====================
        # 合约收益 = 浮动盈亏 + 已实现盈亏（含资金费率收入）
        pnl = float(v.unrealised_pnl) + float(v.realised_pnl)
        
        # ==================== 第4步：获取现货订单信息 ====================
        spot_order_list = rest.find_cex_spot_orders(v.contract)
        if spot_order_list is None:
            logger.warning(f"无法获取 {v.contract} 的现货订单")
            continue

        if len(spot_order_list) == 0:
            logger.warning(f"未找到 {v.contract} 的现货订单")
            continue
        
        # 按更新时间降序排序，获取最新订单
        spot_order_list.sort(key=lambda x: x.update_time_ms, reverse=True)
        
        # ==================== 第5步：计算手续费 ====================
        # 总手续费 = 现货手续费 × 3（开仓 + 平仓 + 其他）
        fee = float(spot_order_list[0].fee) * 3
        spnl = fee  # 初始化现货盈亏为负的手续费
        amount = float(spot_order_list[0].amount)
        
        # ==================== 第6步：获取当前市场行情 ====================
        sticker = rest.get_cex_sticker(v.contract)
        if sticker is None or len(sticker) == 0:
            logger.warning(f"无法获取 {v.contract} 的现货行情")
            time.sleep(1)
            continue

        # ==================== 第7步：检查订单状态 ====================
        if spot_order_list[0].status != "closed":
            logger.warning(f"请手动处理 {v.contract} 仓位，订单状态未关闭")
            continue
        
        # ==================== 第8步：计算现货收益 ====================
        sz = 0.0  # 持仓数量（币）
        if spot_order_list[0].status == "closed":
            # 获取开仓平均价格
            price = float(spot_order_list[0].avg_deal_price)
            
            if spot_order_list[0].side == "sell" and v.size > 0:
                # ========== 现货做空 + 合约做多 ==========
                # 现货做空：借币卖出，需要买回还币
                # 收益 = 卖出价 - 买回价（负数表示亏损）
                sz = amount  # 卖出的币数量
                # 现货盈亏 = -(当前买价 - 开仓卖价) × 数量 - 手续费
                spnl = -(float(sticker[0].highest_bid) - price) * amount + fee
                
            if spot_order_list[0].side == "buy" and v.size < 0:
                # ========== 现货做多 + 合约做空 ==========
                # 现货做多：买入持有，需要卖出平仓
                # 收益 = 卖出价 - 买入价
                sz = float(amount / price)  # 买入的币数量
                # 现货盈亏 = (当前卖价 - 开仓买价) × 数量 - 手续费
                spnl = fee + (float(sticker[0].lowest_ask) - price) * sz

        # ==================== 第9步：确定合约方向 ====================
        side = "long"
        if v.size < 0:
            side = "short"
        
        # ==================== 第10步：输出持仓详情 ====================
        logger.info(f"==================== 交易对 {v.contract} ====================")
        logger.info(f"合约方向：{side} 持仓数量：{v.size} 持仓收益：{pnl}")
        logger.info(f"现货方向：{spot_order_list[0].side} 持仓数量：{sz} 持仓收益：{spnl}")
        logger.info(f"预计总收益：{pnl + spnl}")
        
        # ==================== 第11步：判断是否平仓 ====================
        if pnl + spnl > 0:
            # 总收益为正，执行平仓操作
            logger.info(f"平仓交易对：{v.contract} 总收益：{pnl + spnl}")
            
            # 平掉合约仓位
            rest.cex_futures_close_position(v.contract)
            
            # 平掉现货仓位（反向操作）
            if side == "long":
                # 合约做多 → 现货做空 → 需要买回还币
                rest.cex_spot_place(v.contract, "buy", str(float(sticker[0].lowest_ask)*sz))
            if side == "short":
                # 合约做空 → 现货做多 → 需要卖出平仓
                rest.cex_spot_place(v.contract, "sell", str(amount))

def run_funding():
    """
    资金费率套利策略主函数
    
    运行流程：
    1. 设置合约账户为单向持仓模式
    2. 无限循环监控市场
       - 扫描高资金费率的合约
       - 在结算前开仓（收取资金费率）
       - 监控持仓盈利情况
       - 盈利后自动平仓
    3. 异常处理和日志记录
    
    策略特点：
    - 低风险：合约和现货对冲，不承担价格波动风险
    - 自动化：自动寻找机会、开仓、平仓
    - 高频率：每秒扫描一次，不错过任何机会
    
    Returns:
        None
    """
    try:
        # ==================== 初始化：设置持仓模式 ====================
        # 设置为单向持仓模式（不使用双向持仓）
        rest.set_cex_dual_mode(False)
        
        # ==================== 主循环：持续监控和交易 ====================
        logger.info("资金费率套利策略启动，开始监控市场...")
        while True:
            # 步骤1：寻找高资金费率合约并开仓
            watch_history_funding()
            
            # 步骤2：监控持仓并在盈利时平仓
            watch_position()
            
            # 每秒扫描一次
            time.sleep(1)
            
    except KeyboardInterrupt:
        # 用户按 Ctrl+C 中断程序
        logger.info("程序被用户中断")
    except Exception as e:
        # 捕获所有异常，避免程序崩溃
        logger.error(f"程序运行出现异常: {e}")

