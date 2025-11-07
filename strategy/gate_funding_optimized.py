"""
资金费率套利策略 (Funding Rate Arbitrage Strategy) - 优化版

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
优化内容 (v2.0)
============================================================
1. 日志优化
   - 结构化日志格式
   - 关键信息完整打印
   - 性能监控
   - 日志轮转

2. 异步优化
   - 并发获取行情数据
   - 批量API调用
   - 减少等待时间

3. 逻辑优化
   - 提前返回
   - 减少嵌套
   - 清晰的变量命名
   - 防御性编程

4. 运算优化
   - 避免重复计算
   - 常量提取
   - 类型转换优化
   - 计算结果缓存

============================================================
"""

import rest
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json

# ==================== 数据类定义 ====================

@dataclass
class TradingConfig:
    """交易配置"""
    fee_rate: float = 0.062 / 100.0 * 3  # 交易费率（开仓+平仓+现货）
    balance: float = 200.0  # 单边余额
    leverage: str = "2"  # 杠杆倍数
    min_funding_rate: float = 0.003  # 最低资金费率阈值（0.3%）
    settlement_buffer: int = 10  # 结算前多少秒开仓
    order_wait_time: int = 30  # 订单等待时间
    max_workers: int = 5  # 并发线程数


@dataclass
class MarketData:
    """市场数据"""
    contract_name: str
    funding_rate: float
    funding_interval: int
    quanto_multiplier: float
    futures_ask: float  # 合约卖一价
    futures_bid: float  # 合约买一价
    spot_ask: float  # 现货卖一价
    spot_bid: float  # 现货买一价


@dataclass
class PositionInfo:
    """持仓信息"""
    contract: str
    size: int
    side: str  # 'long' or 'short'
    futures_pnl: float
    spot_pnl: float
    total_pnl: float
    spot_order_price: float
    spot_order_amount: float
    spot_order_side: str


# ==================== 日志配置 ====================

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str, log_file: str = 'logs/funding_strategy.log'):
        """
        初始化结构化日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 移除现有的处理器
        self.logger.handlers.clear()
        
        # ========== 控制台处理器 ==========
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # ========== 文件处理器（带轮转） ==========
        try:
            import os
            os.makedirs('logs', exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"无法创建日志文件: {e}")
        
        self.logger.addHandler(console_handler)
    
    def info(self, msg: str, **kwargs):
        """记录INFO级别日志"""
        extra_info = f" | {json.dumps(kwargs, ensure_ascii=False)}" if kwargs else ""
        self.logger.info(f"{msg}{extra_info}")
    
    def warning(self, msg: str, **kwargs):
        """记录WARNING级别日志"""
        extra_info = f" | {json.dumps(kwargs, ensure_ascii=False)}" if kwargs else ""
        self.logger.warning(f"{msg}{extra_info}")
    
    def error(self, msg: str, **kwargs):
        """记录ERROR级别日志"""
        extra_info = f" | {json.dumps(kwargs, ensure_ascii=False)}" if kwargs else ""
        self.logger.error(f"{msg}{extra_info}")
    
    def debug(self, msg: str, **kwargs):
        """记录DEBUG级别日志"""
        extra_info = f" | {json.dumps(kwargs, ensure_ascii=False)}" if kwargs else ""
        self.logger.debug(f"{msg}{extra_info}")
    
    def performance(self, func_name: str, duration: float, **kwargs):
        """记录性能日志"""
        self.info(f"⏱️  性能统计: {func_name} 耗时 {duration:.3f}秒", **kwargs)


# ==================== 初始化 ====================

# 全局配置
config = TradingConfig()

# 结构化日志记录器
logger = StructuredLogger(__name__)

# 合约缓存
contract_cache: Dict[str, any] = {}

# 线程池
executor = ThreadPoolExecutor(max_workers=config.max_workers)


# ==================== 性能计时装饰器 ====================

def timing_decorator(func):
    """性能计时装饰器"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        if duration > 0.5:  # 只记录耗时超过0.5秒的操作
            logger.performance(func.__name__, duration)
        return result
    return wrapper


# ==================== 核心功能函数 ====================

@timing_decorator
def fetch_contracts() -> Optional[List]:
    """
    获取所有合约列表
    
    Returns:
        合约列表或 None
    """
    try:
        contracts = rest.get_cex_contracts()
        if contracts is None:
            logger.warning("获取合约列表失败：API返回None")
            return None
        
        logger.debug(f"成功获取 {len(contracts)} 个合约")
        return contracts
    except Exception as e:
        logger.error(f"获取合约列表异常", error=str(e))
        return None


def calculate_funding_priority(funding_rate: float, funding_interval: int) -> float:
    """
    计算资金费率优先级（年化收益率）
    
    Args:
        funding_rate: 资金费率（小数形式，如 0.001 = 0.1%）
        funding_interval: 结算间隔（秒）
    
    Returns:
        优先级分数（越高越优）
    """
    # 资金费率百分比
    rate_percent = abs(funding_rate * 100.0)
    # 每日结算次数
    daily_settlements = (24 * 3600) / funding_interval
    # 年化收益率 = 单次费率 × 每日次数 × 365
    annual_rate = rate_percent * daily_settlements * 365
    return annual_rate


def validate_contract_availability(contract_name: str) -> bool:
    """
    验证合约是否可用（通过获取K线数据）
    
    Args:
        contract_name: 合约名称
    
    Returns:
        True=可用，False=不可用
    """
    try:
        candle = rest.get_cex_spot_candle(contract_name, "1m", 1)
        return candle is not None and len(candle) > 0
    except Exception as e:
        logger.debug(f"验证合约 {contract_name} 可用性失败", error=str(e))
        return False


@timing_decorator
def filter_high_funding_contracts() -> Optional[any]:
    """
    筛选高资金费率的合约（优化版）
    
    优化点：
    1. 提前返回，减少嵌套
    2. 批量验证合约可用性（并发）
    3. 缓存已验证的合约
    4. 结构化日志
    
    Returns:
        资金费率最高的合约对象或 None
    """
    # ========== 第1步：获取合约列表 ==========
    contracts = fetch_contracts()
    if not contracts:
        return None
    
    # ========== 第2步：初步筛选高费率合约 ==========
    high_rate_contracts = []
    
    for contract in contracts:
        funding_rate = float(contract.funding_rate)
        funding_rate_percent = funding_rate * 100.0
        
        # 只关注绝对值 > 0.3% 的合约
        if abs(funding_rate_percent) < config.min_funding_rate * 100:
            continue
        
        # 检查缓存
        if contract.name in contract_cache:
            high_rate_contracts.append(contract)
            logger.debug(f"合约 {contract.name} 已在缓存中", 
                        funding_rate=f"{funding_rate_percent:.3f}%")
        else:
            # 需要验证的合约
            high_rate_contracts.append(contract)
    
    if not high_rate_contracts:
        logger.debug("未找到符合条件的高费率合约")
        return None
    
    logger.info(f"📊 找到 {len(high_rate_contracts)} 个高费率合约")
    
    # ========== 第3步：并发验证合约可用性 ==========
    validated_contracts = []
    
    # 分离已验证和未验证的合约
    to_validate = [c for c in high_rate_contracts if c.name not in contract_cache]
    already_validated = [c for c in high_rate_contracts if c.name in contract_cache]
    
    validated_contracts.extend(already_validated)
    
    # 并发验证未验证的合约
    if to_validate:
        logger.debug(f"并发验证 {len(to_validate)} 个新合约")
        
        futures = {
            executor.submit(validate_contract_availability, c.name): c 
            for c in to_validate
        }
        
        for future in as_completed(futures):
            contract = futures[future]
            try:
                if future.result():
                    contract_cache[contract.name] = contract
                    validated_contracts.append(contract)
                    
                    rate = float(contract.funding_rate) * 100.0
                    logger.info(f"✅ 新合约可用: {contract.name}", 
                              funding_rate=f"{rate:.3f}%")
            except Exception as e:
                logger.debug(f"验证合约 {contract.name} 失败", error=str(e))
    
    if not validated_contracts:
        logger.warning("没有可用的合约")
        return None
    
    # ========== 第4步：按优先级排序 ==========
    validated_contracts.sort(
        key=lambda x: calculate_funding_priority(
            float(x.funding_rate), 
            int(x.funding_interval)
        ),
        reverse=True
    )
    
    # ========== 第5步：返回最优合约 ==========
    best_contract = validated_contracts[0]
    rate = float(best_contract.funding_rate) * 100.0
    priority = calculate_funding_priority(
        float(best_contract.funding_rate),
        int(best_contract.funding_interval)
    )
    
    logger.info(
        f"🎯 最优合约: {best_contract.name}",
        funding_rate=f"{rate:.3f}%",
        annual_rate=f"{priority:.2f}%",
        interval_hours=best_contract.funding_interval / 3600
    )
    
    return best_contract


def fetch_market_data(contract_name: str) -> Optional[MarketData]:
    """
    并发获取市场数据（合约和现货行情）
    
    Args:
        contract_name: 合约名称
    
    Returns:
        市场数据对象或 None
    """
    def get_futures_ticker():
        return rest.get_cex_fticker(contract_name)
    
    def get_spot_ticker():
        return rest.get_cex_sticker(contract_name)
    
    try:
        # 并发获取行情数据
        future_futures = executor.submit(get_futures_ticker)
        future_spot = executor.submit(get_spot_ticker)
        
        futures_ticker = future_futures.result(timeout=5)
        spot_ticker = future_spot.result(timeout=5)
        
        # 验证数据
        if not futures_ticker or len(futures_ticker) == 0:
            logger.warning(f"合约行情数据为空", contract=contract_name)
            return None
        
        if not spot_ticker or len(spot_ticker) == 0:
            logger.warning(f"现货行情数据为空", contract=contract_name)
            return None
        
        # 获取合约信息
        contract_info = contract_cache.get(contract_name)
        if not contract_info:
            logger.warning(f"合约信息不在缓存中", contract=contract_name)
            return None
        
        # 构建市场数据
        market_data = MarketData(
            contract_name=contract_name,
            funding_rate=float(contract_info.funding_rate),
            funding_interval=int(contract_info.funding_interval),
            quanto_multiplier=float(contract_info.quanto_multiplier),
            futures_ask=float(futures_ticker[0].lowest_ask),
            futures_bid=float(futures_ticker[0].highest_bid),
            spot_ask=float(spot_ticker[0].lowest_ask),
            spot_bid=float(spot_ticker[0].highest_bid)
        )
        
        logger.debug(
            f"市场数据",
            contract=contract_name,
            f_bid=market_data.futures_bid,
            f_ask=market_data.futures_ask,
            s_ask=market_data.spot_ask
        )
        
        return market_data
        
    except Exception as e:
        logger.error(f"获取市场数据失败", contract=contract_name, error=str(e))
        return None


def is_near_settlement(funding_interval: int, buffer_seconds: int = 10) -> bool:
    """
    判断是否接近资金费率结算时间
    
    Args:
        funding_interval: 结算间隔（秒）
        buffer_seconds: 结算前多少秒（默认10秒）
    
    Returns:
        True=接近结算时间，False=不接近
    """
    current_timestamp = int(time.time())
    time_in_interval = current_timestamp % funding_interval
    remaining_time = funding_interval - time_in_interval
    
    is_near = remaining_time <= buffer_seconds
    
    if is_near:
        logger.info(
            f"⏰ 接近结算时间",
            remaining_seconds=remaining_time,
            settlement_time=datetime.fromtimestamp(
                current_timestamp + remaining_time
            ).strftime('%H:%M:%S')
        )
    
    return is_near


def calculate_order_size(
    market_data: MarketData,
    balance: float,
    is_positive_rate: bool
) -> Optional[Tuple[float, int]]:
    """
    计算开仓数量（优化版）
    
    Args:
        market_data: 市场数据
        balance: 余额
        is_positive_rate: 是否为正资金费率
    
    Returns:
        (现货金额, 合约张数) 或 None
    """
    try:
        if is_positive_rate:
            # 正费率：合约做空 + 现货做多
            price_ref = market_data.futures_bid
            spot_price = market_data.spot_ask
        else:
            # 负费率：合约做多 + 现货做空
            price_ref = market_data.futures_ask
            spot_price = market_data.spot_ask
        
        # 计算币数量
        coin_amount = balance / price_ref
        
        # 计算合约张数
        contract_size = coin_amount / market_data.quanto_multiplier
        contract_size_int = int(contract_size)
        
        # 张数必须 >= 1
        if contract_size_int < 1:
            logger.warning(
                f"合约张数不足1张",
                calculated=contract_size,
                balance=balance,
                price=price_ref
            )
            return None
        
        # 计算现货金额（留1%余量）
        spot_amount = spot_price * coin_amount * 1.01
        
        logger.info(
            f"📐 计算开仓数量",
            coin_amount=f"{coin_amount:.4f}",
            contract_size=contract_size_int,
            spot_amount=f"{spot_amount:.2f} USDT"
        )
        
        return (spot_amount, contract_size_int)
        
    except Exception as e:
        logger.error(f"计算开仓数量失败", error=str(e))
        return None


@timing_decorator
def execute_arbitrage_strategy():
    """
    执行资金费率套利策略（优化版）
    
    优化点：
    1. 提前返回，减少嵌套
    2. 结构化日志
    3. 并发获取数据
    4. 优化判断逻辑
    """
    # ========== 第1步：检查是否已有持仓 ==========
    positions = rest.get_cex_all_position()
    if positions and len(positions) > 0:
        logger.debug(f"已有 {len(positions)} 个持仓，跳过开仓")
        return
    
    # ========== 第2步：筛选最优合约 ==========
    best_contract = filter_high_funding_contracts()
    if not best_contract:
        return
    
    # ========== 第3步：检查是否接近结算时间 ==========
    if not is_near_settlement(
        int(best_contract.funding_interval),
        config.settlement_buffer
    ):
        return
    
    # ========== 第4步：获取市场数据 ==========
    market_data = fetch_market_data(best_contract.name)
    if not market_data:
        return
    
    # ========== 第5步：检查钱包余额 ==========
    wallet = rest.get_cex_wallet_balance()
    if not wallet:
        logger.warning("无法获取钱包余额")
        return
    
    spot_balance = float(wallet.details["spot"].amount)
    required_balance = config.balance * 2
    
    if spot_balance < required_balance:
        logger.warning(
            f"💰 余额不足",
            current=f"{spot_balance:.2f} USDT",
            required=f"{required_balance:.2f} USDT"
        )
        return
    
    logger.info(
        f"💰 余额充足",
        current=f"{spot_balance:.2f} USDT",
        required=f"{required_balance:.2f} USDT"
    )
    
    # ========== 第6步：设置杠杆 ==========
    coin_symbol = best_contract.name.split("_")[0]
    rest.set_cex_margin_leverage(best_contract.name, config.leverage)
    rest.set_cex_leverage(best_contract.name, config.leverage)
    
    logger.info(f"⚙️  设置杠杆倍数: {config.leverage}x")
    
    # ========== 第7步：计算开仓数量 ==========
    funding_rate_percent = market_data.funding_rate * 100.0
    is_positive_rate = funding_rate_percent > 0
    
    order_size = calculate_order_size(
        market_data,
        config.balance,
        is_positive_rate
    )
    
    if not order_size:
        return
    
    spot_amount, contract_size = order_size
    
    # ========== 第8步：执行开仓 ==========
    if is_positive_rate:
        # 正费率：合约做空(-) + 现货做多
        logger.info(f"📈 执行正费率套利: 合约做空 + 现货做多")
        execute_hedge_order(
            best_contract.name,
            spot_amount,
            -contract_size,  # 负数表示做空
            "short"
        )
    else:
        # 负费率：合约做多(+) + 现货做空
        logger.info(f"📉 执行负费率套利: 合约做多 + 现货做空")
        execute_hedge_order(
            best_contract.name,
            spot_amount,
            contract_size,  # 正数表示做多
            "long"
        )


def execute_hedge_order(
    contract_name: str,
    spot_amount: float,
    contract_size: int,
    strategy_type: str
):
    """
    执行对冲开仓（优化版）
    
    Args:
        contract_name: 合约名称
        spot_amount: 现货金额
        contract_size: 合约张数（正数=做多，负数=做空）
        strategy_type: 策略类型（'long' or 'short'）
    """
    # ========== 第1步：检查是否已有持仓 ==========
    existing_position = rest.get_cex_position(contract_name)
    if existing_position and existing_position.size != 0:
        logger.warning(f"⚠️  合约已有持仓，跳过", contract=contract_name)
        return
    
    # ========== 第2步：设置杠杆 ==========
    coin_symbol = contract_name.split("_")[0]
    rest.set_cex_unified_leverage(coin_symbol, config.leverage)
    rest.set_cex_leverage(contract_name, config.leverage)
    
    # ========== 第3步：执行开仓 ==========
    if strategy_type == "long":
        # 策略A：合约做多 + 现货做空
        _execute_long_hedge(contract_name, spot_amount, contract_size)
    else:
        # 策略B：合约做空 + 现货做多
        _execute_short_hedge(contract_name, spot_amount, contract_size)


def _execute_long_hedge(contract_name: str, spot_amount: float, contract_size: int):
    """
    执行做多对冲：合约做多 + 现货做空
    
    Args:
        contract_name: 合约名称
        spot_amount: 现货金额
        contract_size: 合约张数
    """
    logger.info(
        f"🔵 开始执行做多对冲",
        contract=contract_name,
        futures_size=contract_size,
        spot_amount=f"{spot_amount:.2f}"
    )
    
    # 第1步：开合约多单
    futures_order = rest.cex_futures_place(contract_name, "0", contract_size)
    if not futures_order:
        logger.error(f"❌ 合约多单失败", contract=contract_name)
        return
    
    logger.info(f"✅ 合约多单成功", order_id=futures_order.id)
    
    # 第2步：开现货空单
    if futures_order.id:
        spot_order = rest.cex_spot_place(contract_name, "sell", str(spot_amount))
        if not spot_order:
            logger.error(f"❌ 现货空单失败，回滚合约仓位")
            rest.cex_futures_close_position(contract_name)
            return
        
        logger.info(f"✅ 现货空单成功", order_id=spot_order.id)
        logger.info(f"🎉 对冲开仓完成，等待 {config.order_wait_time} 秒")
        time.sleep(config.order_wait_time)


def _execute_short_hedge(contract_name: str, spot_amount: float, contract_size: int):
    """
    执行做空对冲：合约做空 + 现货做多
    
    Args:
        contract_name: 合约名称
        spot_amount: 现货金额
        contract_size: 合约张数（负数）
    """
    logger.info(
        f"🔴 开始执行做空对冲",
        contract=contract_name,
        futures_size=contract_size,
        spot_amount=f"{spot_amount:.2f}"
    )
    
    # 第1步：开合约空单
    futures_order = rest.cex_futures_place(contract_name, "0", contract_size)
    if not futures_order:
        logger.error(f"❌ 合约空单失败", contract=contract_name)
        return
    
    logger.info(f"✅ 合约空单成功", order_id=futures_order.id)
    
    # 第2步：开现货多单
    if futures_order.id:
        spot_order = rest.cex_spot_place(contract_name, "buy", str(spot_amount))
        if not spot_order:
            logger.error(f"❌ 现货多单失败，回滚合约仓位")
            rest.cex_futures_close_position(contract_name)
            return
        
        logger.info(f"✅ 现货多单成功", order_id=spot_order.id)
        logger.info(f"🎉 对冲开仓完成，等待 {config.order_wait_time} 秒")
        time.sleep(config.order_wait_time)


@timing_decorator
def monitor_and_close_positions():
    """
    监控持仓并自动平仓（优化版）
    
    优化点：
    1. 提前返回
    2. 并发获取数据
    3. 结构化日志
    4. 详细的盈亏计算
    """
    # ========== 第1步：获取所有持仓 ==========
    positions = rest.get_cex_all_position()
    if not positions:
        logger.debug("当前无持仓")
        return
    
    logger.debug(f"监控 {len(positions)} 个持仓")
    
    # ========== 第2步：遍历每个持仓 ==========
    for position in positions:
        position_info = _analyze_position(position)
        if not position_info:
            continue
        
        # 输出持仓详情
        _log_position_info(position_info)
        
        # 判断是否平仓
        if position_info.total_pnl > 0:
            _close_profitable_position(position_info)


def _analyze_position(position) -> Optional[PositionInfo]:
    """
    分析单个持仓
    
    Args:
        position: 持仓对象
    
    Returns:
        持仓信息对象或 None
    """
    contract_name = position.contract
    
    # 计算合约收益
    futures_pnl = float(position.unrealised_pnl) + float(position.realised_pnl)
    
    # 获取现货订单
    spot_orders = rest.find_cex_spot_orders(contract_name)
    if not spot_orders or len(spot_orders) == 0:
        logger.warning(f"未找到现货订单", contract=contract_name)
        return None
    
    # 获取最新订单
    spot_orders.sort(key=lambda x: x.update_time_ms, reverse=True)
    latest_order = spot_orders[0]
    
    # 检查订单状态
    if latest_order.status != "closed":
        logger.warning(
            f"现货订单未关闭",
            contract=contract_name,
            status=latest_order.status
        )
        return None
    
    # 获取当前行情
    spot_ticker = rest.get_cex_sticker(contract_name)
    if not spot_ticker or len(spot_ticker) == 0:
        logger.warning(f"无法获取现货行情", contract=contract_name)
        return None
    
    # 计算现货收益
    fee = float(latest_order.fee) * 3
    spot_pnl = _calculate_spot_pnl(
        latest_order,
        spot_ticker[0],
        position.size,
        fee
    )
    
    # 确定合约方向
    side = "long" if position.size > 0 else "short"
    
    # 构建持仓信息
    return PositionInfo(
        contract=contract_name,
        size=position.size,
        side=side,
        futures_pnl=futures_pnl,
        spot_pnl=spot_pnl,
        total_pnl=futures_pnl + spot_pnl,
        spot_order_price=float(latest_order.avg_deal_price),
        spot_order_amount=float(latest_order.amount),
        spot_order_side=latest_order.side
    )


def _calculate_spot_pnl(
    spot_order,
    current_ticker,
    position_size: int,
    fee: float
) -> float:
    """
    计算现货盈亏
    
    Args:
        spot_order: 现货订单
        current_ticker: 当前行情
        position_size: 合约持仓数量
        fee: 手续费
    
    Returns:
        现货盈亏
    """
    open_price = float(spot_order.avg_deal_price)
    amount = float(spot_order.amount)
    
    if spot_order.side == "sell" and position_size > 0:
        # 现货做空 + 合约做多
        current_price = float(current_ticker.highest_bid)
        spot_pnl = (open_price - current_price) * amount - fee
    elif spot_order.side == "buy" and position_size < 0:
        # 现货做多 + 合约做空
        current_price = float(current_ticker.lowest_ask)
        coin_amount = amount / open_price
        spot_pnl = (current_price - open_price) * coin_amount - fee
    else:
        spot_pnl = -fee
    
    return spot_pnl


def _log_position_info(info: PositionInfo):
    """
    输出持仓详情日志
    
    Args:
        info: 持仓信息
    """
    logger.info(f"=" * 80)
    logger.info(
        f"📊 持仓详情",
        contract=info.contract,
        side=info.side,
        size=info.size
    )
    logger.info(
        f"💵 合约收益",
        pnl=f"{info.futures_pnl:.4f} USDT"
    )
    logger.info(
        f"💵 现货收益",
        pnl=f"{info.spot_pnl:.4f} USDT",
        side=info.spot_order_side
    )
    logger.info(
        f"💰 总收益",
        pnl=f"{info.total_pnl:.4f} USDT",
        status="🟢 盈利" if info.total_pnl > 0 else "🔴 亏损"
    )
    logger.info(f"=" * 80)


def _close_profitable_position(info: PositionInfo):
    """
    平掉盈利的仓位
    
    Args:
        info: 持仓信息
    """
    logger.info(
        f"🎯 准备平仓",
        contract=info.contract,
        total_pnl=f"{info.total_pnl:.4f} USDT"
    )
    
    # 平掉合约仓位
    rest.cex_futures_close_position(info.contract)
    logger.info(f"✅ 合约仓位已平仓")
    
    # 平掉现货仓位
    spot_ticker = rest.get_cex_sticker(info.contract)
    if not spot_ticker or len(spot_ticker) == 0:
        logger.error(f"❌ 无法获取现货行情，请手动平仓")
        return
    
    if info.side == "long":
        # 合约做多 → 现货做空 → 需要买回还币
        amount = info.spot_order_amount
        price = float(spot_ticker[0].lowest_ask)
        spot_order = rest.cex_spot_place(
            info.contract,
            "buy",
            str(price * amount)
        )
    else:
        # 合约做空 → 现货做多 → 需要卖出平仓
        amount = info.spot_order_amount / info.spot_order_price
        spot_order = rest.cex_spot_place(
            info.contract,
            "sell",
            str(amount)
        )
    
    if spot_order:
        logger.info(f"✅ 现货仓位已平仓")
        logger.info(f"🎉 平仓完成！总收益: {info.total_pnl:.4f} USDT")
    else:
        logger.error(f"❌ 现货平仓失败，请手动处理")


def run_funding_strategy():
    """
    资金费率套利策略主函数（优化版）
    
    优化点：
    1. 结构化日志
    2. 性能监控
    3. 异常处理
    4. 优雅退出
    """
    try:
        # ========== 初始化 ==========
        logger.info("=" * 80)
        logger.info("🚀 资金费率套利策略启动 v2.0")
        logger.info(f"⚙️  配置: 余额={config.balance} USDT, 杠杆={config.leverage}x")
        logger.info(f"⚙️  最低费率阈值: {config.min_funding_rate*100:.2f}%")
        logger.info("=" * 80)
        
        # 设置持仓模式
        rest.set_cex_dual_mode(False)
        logger.info("✅ 持仓模式已设置为单向模式")
        
        # ========== 主循环 ==========
        loop_count = 0
        start_time = time.time()
        
        while True:
            loop_count += 1
            
            # 每100次循环输出一次统计
            if loop_count % 100 == 0:
                runtime = time.time() - start_time
                logger.info(
                    f"📈 运行统计",
                    loops=loop_count,
                    runtime=f"{runtime/3600:.2f} 小时",
                    avg_loop_time=f"{runtime/loop_count:.2f} 秒"
                )
            
            # 执行策略
            execute_arbitrage_strategy()
            monitor_and_close_positions()
            
            # 休眠1秒
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("👋 程序被用户中断")
        logger.info(f"📊 总循环次数: {loop_count}")
    
    except Exception as e:
        logger.error(f"💥 程序异常", error=str(e), error_type=type(e).__name__)
        raise
    
    finally:
        logger.info("🛑 程序退出")
        executor.shutdown(wait=True)


# ==================== 程序入口 ====================

if __name__ == "__main__":
    """
    程序入口
    
    使用方法：
        python gate_funding_optimized.py
    
    退出方法：
        按 Ctrl+C 中断程序
    """
    run_funding_strategy()

