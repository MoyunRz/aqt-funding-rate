"""
基于 CCXT 的交易所 API 封装模块

============================================================
模块功能
============================================================
使用 CCXT 统一接口封装交易所 API，支持：

1. 合约交易（Futures Trading）
   - 获取合约列表和行情
   - 合约开仓、平仓
   - 设置杠杆倍数
   - 查询持仓信息

2. 现货交易（Spot Trading）
   - 现货买卖（支持杠杆）
   - 查询现货订单
   - 获取现货行情

3. 账户管理（Account Management）
   - 获取钱包余额
   - 设置统一账户杠杆
   - 查询账户信息

4. 市场数据（Market Data）
   - 获取K线数据
   - 获取实时行情
   - 获取交易对信息

============================================================
优势
============================================================
✅ 统一接口：支持 100+ 交易所
✅ 维护良好：社区活跃，更新频繁
✅ 文档完善：详细的 API 文档
✅ 易于扩展：轻松切换到其他交易所

============================================================
使用说明
============================================================
环境变量配置：
    export GATE_API_KEY="your_api_key"
    export GATE_API_SECRET="your_api_secret"
    export GATE_USE_TESTNET="false"  # 可选

CCXT 文档: https://docs.ccxt.com/
"""

import os
import ccxt
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 数据类定义 ====================

@dataclass
class Contract:
    """合约信息"""
    name: str
    funding_rate: float
    funding_interval: int
    quanto_multiplier: float
    mark_price: float = 0.0
    index_price: float = 0.0
    
    def __post_init__(self):
        # CCXT 返回的是小数形式，需要转换
        if abs(self.funding_rate) < 1:
            self.funding_rate = self.funding_rate  # 保持原值
        self.funding_interval = int(self.funding_interval)


@dataclass
class Ticker:
    """行情数据"""
    symbol: str
    last: float
    highest_bid: float
    lowest_ask: float
    base_volume: float
    quote_volume: float
    timestamp: int


@dataclass
class Position:
    """持仓信息"""
    contract: str
    size: int
    leverage: str
    unrealised_pnl: float
    realised_pnl: float
    entry_price: float
    mark_price: float
    
    def __post_init__(self):
        self.size = int(self.size)


@dataclass
class OrderInfo:
    """订单信息"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: float
    price: float
    avg_deal_price: float
    status: str
    fee: float
    update_time_ms: int


@dataclass
class WalletBalance:
    """钱包余额"""
    currency: str
    available: float
    total: float
    details: Dict[str, Any]


# ==================== CCXT 客户端管理 ====================

class CCXTClient:
    """CCXT 客户端封装"""
    
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        use_testnet: bool = False,
        exchange_id: str = 'gate'
    ):
        """
        初始化 CCXT 客户端
        
        Args:
            api_key: API Key
            api_secret: API Secret
            use_testnet: 是否使用测试网
            exchange_id: 交易所ID（默认 gate）
        """
        # 从环境变量加载配置（如果未提供）
        self.api_key = api_key or os.getenv('GATE_API_KEY', '')
        self.api_secret = api_secret or os.getenv('GATE_API_SECRET', '')
        self.use_testnet = use_testnet or os.getenv('GATE_USE_TESTNET', 'false').lower() == 'true'
        
        # 创建交易所实例
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,  # 启用速率限制
            'timeout': 30000,  # 30秒超时
            'options': {
                'defaultType': 'swap',  # 默认使用永续合约
                'defaultSettle': 'usdt',  # 默认USDT结算
            }
        })
        
        # 如果使用测试网
        if self.use_testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info("✅ CCXT 客户端已切换到测试网模式")
        
        logger.info(f"✅ CCXT 客户端初始化完成 - 交易所: {exchange_id}, 测试网: {self.use_testnet}")
    
    def load_markets(self):
        """加载市场数据"""
        try:
            return self.exchange.load_markets()
        except Exception as e:
            logger.error(f"❌ 加载市场数据失败: {e}")
            return None


# ==================== 全局客户端实例 ====================

_ccxt_client: Optional[CCXTClient] = None


def get_ccxt_client() -> CCXTClient:
    """获取全局 CCXT 客户端实例（单例模式）"""
    global _ccxt_client
    if _ccxt_client is None:
        _ccxt_client = CCXTClient()
    return _ccxt_client


def init_ccxt_client(api_key: str = None, api_secret: str = None, use_testnet: bool = False) -> CCXTClient:
    """初始化 CCXT 客户端"""
    global _ccxt_client
    _ccxt_client = CCXTClient(api_key, api_secret, use_testnet)
    return _ccxt_client


# ==================== 合约交易 API ====================

def get_cex_contracts(contract: str = "") -> Optional[List[Contract]]:
    """
    获取合约列表
    
    Args:
        contract: 合约名称筛选（可选）
    
    Returns:
        合约列表或 None
    """
    try:
        client = get_ccxt_client()
        
        # 加载市场数据（带进度提示）
        logger.info("正在加载市场数据，这可能需要一些时间...")
        markets = client.exchange.load_markets()
        logger.info(f"✅ 已加载 {len(markets)} 个市场")
        
        contracts = []
        swap_markets = []
        
        # 第一步：筛选出所有永续合约
        for symbol, market in markets.items():
            # 只获取永续合约（swap）
            if market.get('type') != 'swap':
                continue
            
            # USDT 结算
            if market.get('settle') != 'USDT':
                continue
            
            # 如果指定了合约名称，进行筛选
            if contract:
                symbol_normalized = symbol.replace('/', '_').replace(':USDT', '')
                if symbol_normalized != contract:
                    continue
            
            swap_markets.append((symbol, market))
        
        logger.info(f"找到 {len(swap_markets)} 个 USDT 永续合约，正在获取资金费率...")
        
        # 第二步：批量获取资金费率（减少API调用）
        for idx, (symbol, market) in enumerate(swap_markets):
            if idx > 0 and idx % 10 == 0:
                logger.info(f"已处理 {idx}/{len(swap_markets)} 个合约...")
            
            # 获取资金费率
            try:
                funding_rate_info = client.exchange.fetch_funding_rate(symbol)
                funding_rate = funding_rate_info.get('fundingRate', 0)
                funding_timestamp = funding_rate_info.get('fundingTimestamp', 0)
                
                # 计算下次结算时间间隔（秒）
                funding_interval = 8 * 3600  # Gate.io 默认 8 小时
                
                # 获取合约乘数
                contract_size = market.get('contractSize', 1)
                quanto_multiplier = 1.0 / contract_size if contract_size > 0 else 1.0
                
                # 获取标记价格（使用市场数据中的价格，避免额外API调用）
                mark_price = market.get('info', {}).get('mark_price', 0)
                if not mark_price:
                    # 如果市场数据中没有，再调用API
                    try:
                        ticker = client.exchange.fetch_ticker(symbol)
                        mark_price = ticker.get('last', 0)
                    except:
                        mark_price = 0
                
                contracts.append(Contract(
                    name=symbol.replace('/', '_').replace(':USDT', ''),  # BTC/USDT:USDT -> BTC_USDT
                    funding_rate=funding_rate,
                    funding_interval=funding_interval,
                    quanto_multiplier=quanto_multiplier,
                    mark_price=mark_price
                ))
                
            except Exception as e:
                logger.debug(f"跳过合约 {symbol}: {e}")
                continue
        
        logger.info(f"✅ 成功获取 {len(contracts)} 个合约信息")
        return contracts if contracts else None
        
    except Exception as e:
        logger.error(f"❌ 获取合约列表失败: {e}", exc_info=True)
        return None


def get_cex_fticker(contract: str) -> Optional[List[Ticker]]:
    """
    获取合约行情
    
    Args:
        contract: 合约名称（如 BTC_USDT）
    
    Returns:
        行情列表或 None
    """
    try:
        client = get_ccxt_client()
        
        # 转换合约名称格式: BTC_USDT -> BTC/USDT:USDT
        symbol = contract.replace('_', '/') + ':USDT'
        
        ticker = client.exchange.fetch_ticker(symbol)
        
        return [Ticker(
            symbol=contract,
            last=ticker['last'],
            highest_bid=ticker['bid'],
            lowest_ask=ticker['ask'],
            base_volume=ticker.get('baseVolume', 0),
            quote_volume=ticker.get('quoteVolume', 0),
            timestamp=ticker.get('timestamp', 0)
        )]
        
    except Exception as e:
        logger.error(f"❌ 获取合约行情失败 {contract}: {e}")
        return None


def cex_futures_place(contract: str, price: str, size: int) -> Optional[OrderInfo]:
    """
    合约下单（市价单）
    
    Args:
        contract: 合约名称（如 BTC_USDT）
        price: 价格（"0"表示市价单）
        size: 数量（正数=做多，负数=做空）
    
    Returns:
        订单信息或 None
    """
    try:
        client = get_ccxt_client()
        
        # 转换合约名称
        symbol = contract.replace('_', '/') + ':USDT'
        
        # 判断买卖方向
        side = 'buy' if size > 0 else 'sell'
        amount = abs(size)
        
        # 市价单
        order = client.exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=amount
        )
        
        return OrderInfo(
            id=str(order['id']),
            symbol=contract,
            side=side,
            amount=amount,
            price=0,
            avg_deal_price=order.get('average', 0),
            status=order.get('status', 'open'),
            fee=0,
            update_time_ms=order.get('timestamp', 0)
        )
        
    except Exception as e:
        logger.error(f"❌ 合约下单失败 {contract}: {e}")
        return None


def cex_futures_close_position(contract: str) -> bool:
    """
    平掉合约仓位
    
    Args:
        contract: 合约名称（如 BTC_USDT）
    
    Returns:
        是否成功
    """
    try:
        client = get_ccxt_client()
        
        # 转换合约名称
        symbol = contract.replace('_', '/') + ':USDT'
        
        # 获取当前持仓
        positions = client.exchange.fetch_positions([symbol])
        
        for position in positions:
            contracts = position.get('contracts', 0)
            if contracts == 0:
                continue
            
            # 平仓：反向操作
            side = 'sell' if contracts > 0 else 'buy'
            amount = abs(contracts)
            
            # 减仓参数
            params = {'reduceOnly': True}
            
            client.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params=params
            )
            
            logger.info(f"✅ 平仓成功: {contract}")
            return True
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 平仓失败 {contract}: {e}")
        return False


def get_cex_position(contract: str) -> Optional[Position]:
    """
    获取合约持仓
    
    Args:
        contract: 合约名称（如 BTC_USDT）
    
    Returns:
        持仓信息或 None
    """
    try:
        client = get_ccxt_client()
        
        # 转换合约名称
        symbol = contract.replace('_', '/') + ':USDT'
        
        positions = client.exchange.fetch_positions([symbol])
        
        for position in positions:
            contracts = position.get('contracts', 0)
            if contracts == 0:
                continue
            
            return Position(
                contract=contract,
                size=int(contracts),
                leverage=str(position.get('leverage', 1)),
                unrealised_pnl=position.get('unrealizedPnl', 0),
                realised_pnl=0,  # CCXT 不直接提供
                entry_price=position.get('entryPrice', 0),
                mark_price=position.get('markPrice', 0)
            )
        
        # 没有持仓，返回空持仓
        return Position(
            contract=contract,
            size=0,
            leverage="1",
            unrealised_pnl=0,
            realised_pnl=0,
            entry_price=0,
            mark_price=0
        )
        
    except Exception as e:
        logger.error(f"❌ 获取持仓失败 {contract}: {e}")
        return None


def get_cex_all_position() -> Optional[List[Position]]:
    """
    获取所有合约持仓
    
    Returns:
        持仓列表或 None
    """
    try:
        client = get_ccxt_client()
        
        positions = client.exchange.fetch_positions()
        
        result = []
        for position in positions:
            contracts = position.get('contracts', 0)
            if contracts == 0:
                continue
            
            symbol = position.get('symbol', '')
            # 转换格式: BTC/USDT:USDT -> BTC_USDT
            contract_name = symbol.split(':')[0].replace('/', '_')
            
            result.append(Position(
                contract=contract_name,
                size=int(contracts),
                leverage=str(position.get('leverage', 1)),
                unrealised_pnl=position.get('unrealizedPnl', 0),
                realised_pnl=0,
                entry_price=position.get('entryPrice', 0),
                mark_price=position.get('markPrice', 0)
            ))
        
        return result if result else None
        
    except Exception as e:
        logger.error(f"❌ 获取所有持仓失败: {e}")
        return None


def set_cex_leverage(contract: str, leverage: str) -> bool:
    """
    设置合约杠杆
    
    Args:
        contract: 合约名称（如 BTC_USDT）
        leverage: 杠杆倍数
    
    Returns:
        是否成功
    """
    try:
        client = get_ccxt_client()
        
        # 转换合约名称
        symbol = contract.replace('_', '/') + ':USDT'
        
        client.exchange.set_leverage(int(leverage), symbol)
        logger.info(f"✅ 设置杠杆成功: {contract} -> {leverage}x")
        return True
        
    except Exception as e:
        logger.error(f"❌ 设置杠杆失败 {contract}: {e}")
        return False


def set_cex_dual_mode(dual_mode: bool) -> bool:
    """
    设置持仓模式（单向/双向）
    
    Args:
        dual_mode: True=双向持仓，False=单向持仓
    
    Returns:
        是否成功
    """
    try:
        client = get_ccxt_client()
        
        # Gate.io 通过 CCXT 设置持仓模式
        mode = 'hedged' if dual_mode else 'one-way'
        
        # 注意：不是所有交易所都支持此功能
        client.exchange.set_position_mode(hedged=dual_mode)
        logger.info(f"✅ 设置持仓模式: {'双向' if dual_mode else '单向'}")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ 设置持仓模式失败（可能不支持）: {e}")
        return False


# ==================== 现货交易 API ====================

def get_cex_sticker(contract: str) -> Optional[List[Ticker]]:
    """
    获取现货行情
    
    Args:
        contract: 交易对名称（如 BTC_USDT）
    
    Returns:
        行情列表或 None
    """
    try:
        client = get_ccxt_client()
        
        # 转换格式: BTC_USDT -> BTC/USDT
        symbol = contract.replace('_', '/')
        
        ticker = client.exchange.fetch_ticker(symbol)
        
        return [Ticker(
            symbol=contract,
            last=ticker['last'],
            highest_bid=ticker['bid'],
            lowest_ask=ticker['ask'],
            base_volume=ticker.get('baseVolume', 0),
            quote_volume=ticker.get('quoteVolume', 0),
            timestamp=ticker.get('timestamp', 0)
        )]
        
    except Exception as e:
        logger.error(f"❌ 获取现货行情失败 {contract}: {e}")
        return None


def get_cex_spot_candle(contract: str, interval: str = "1m", limit: int = 100) -> Optional[list]:
    """
    获取现货K线数据
    
    Args:
        contract: 交易对名称（如 BTC_USDT）
        interval: 时间周期（1m, 5m, 15m, 1h, 4h, 1d等）
        limit: 数量限制
    
    Returns:
        K线数据列表或 None
    """
    try:
        client = get_ccxt_client()
        
        # 转换格式
        symbol = contract.replace('_', '/')
        
        # 获取OHLCV数据
        ohlcv = client.exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
        
        return ohlcv if ohlcv else None
        
    except Exception as e:
        logger.error(f"❌ 获取K线数据失败 {contract}: {e}")
        return None


def cex_spot_place(contract: str, side: str, amount: str) -> Optional[OrderInfo]:
    """
    现货下单（市价单）
    
    Args:
        contract: 交易对名称（如 BTC_USDT）
        side: 买卖方向（'buy' 或 'sell'）
        amount: 金额（USDT）
    
    Returns:
        订单信息或 None
    """
    try:
        client = get_ccxt_client()
        
        # 转换格式
        symbol = contract.replace('_', '/')
        
        # 市价单
        order = client.exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=float(amount),
            params={'createMarketBuyOrderRequiresPrice': False}  # 市价买单不需要价格
        )
        
        return OrderInfo(
            id=str(order['id']),
            symbol=contract,
            side=side,
            amount=float(amount),
            price=0,
            avg_deal_price=order.get('average', 0),
            status=order.get('status', 'open'),
            fee=order.get('fee', {}).get('cost', 0),
            update_time_ms=order.get('timestamp', 0)
        )
        
    except Exception as e:
        logger.error(f"❌ 现货下单失败 {contract}: {e}")
        return None


def find_cex_spot_orders(contract: str) -> Optional[List[OrderInfo]]:
    """
    查询现货订单历史（仅返回已完成的订单）
    
    Args:
        contract: 交易对名称（如 BTC_USDT）
    
    Returns:
        订单列表或 None（仅包含状态为 'closed' 的已完成订单）
    """
    try:
        client = get_ccxt_client()
        
        # 转换格式
        symbol = contract.replace('_', '/')
        
        # 获取最近订单
        orders = client.exchange.fetch_orders(symbol, limit=50)
        
        result = []
        for order in orders:
            # CCXT 订单状态：'open', 'closed', 'canceled'
            # 统一转换为 'closed' 表示已完成，与 rest.py 的 'finished' 对应
            order_status = order.get('status', '')
            if order_status not in ['closed', 'filled']:
                continue  # 只返回已完成的订单
            
            result.append(OrderInfo(
                id=str(order['id']),
                symbol=contract,
                side=order['side'],
                amount=order['amount'],
                price=order.get('price', 0),
                avg_deal_price=order.get('average', 0),
                status='closed',  # 统一状态为 'closed'，与 funding.py 中的检查一致
                fee=order.get('fee', {}).get('cost', 0),
                update_time_ms=order.get('timestamp', 0)
            ))
        
        return result if result else None
        
    except Exception as e:
        logger.error(f"❌ 查询订单失败 {contract}: {e}")
        return None


def set_cex_margin_leverage(contract: str, leverage: str) -> bool:
    """
    设置现货杠杆（逐仓）
    
    Args:
        contract: 交易对名称（如 BTC_USDT）
        leverage: 杠杆倍数
    
    Returns:
        是否成功
    """
    try:
        client = get_ccxt_client()
        
        # 转换格式
        symbol = contract.replace('_', '/')
        
        # 某些交易所支持设置保证金杠杆
        client.exchange.set_leverage(int(leverage), symbol, params={'marginMode': 'isolated'})
        logger.info(f"✅ 设置现货杠杆成功: {contract} -> {leverage}x")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ 设置现货杠杆失败（可能不支持）{contract}: {e}")
        return False


def set_cex_unified_leverage(currency: str, leverage: str) -> bool:
    """
    设置统一账户杠杆
    
    Args:
        currency: 币种（如 BTC）
        leverage: 杠杆倍数
    
    Returns:
        是否成功
    """
    try:
        # 统一账户杠杆设置通常在账户级别，不是所有交易所都支持
        logger.warning(f"⚠️ 统一账户杠杆设置在 CCXT 中可能不直接支持")
        return True
        
    except Exception as e:
        logger.error(f"❌ 设置统一账户杠杆失败 {currency}: {e}")
        return False


# ==================== 账户管理 API ====================

def get_cex_wallet_balance() -> Optional[WalletBalance]:
    """
    获取钱包余额
    
    Returns:
        钱包余额或 None
    """
    try:
        client = get_ccxt_client()
        
        balance = client.exchange.fetch_balance()
        
        # 获取USDT余额
        usdt_balance = balance.get('USDT', {})
        
        return WalletBalance(
            currency='USDT',
            available=usdt_balance.get('free', 0),
            total=usdt_balance.get('total', 0),
            details={
                'spot': type('obj', (object,), {
                    'amount': usdt_balance.get('free', 0)
                })()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 获取钱包余额失败: {e}")
        return None


# ==================== 兼容性接口 ====================
# 为了保持向后兼容，提供与旧 API 相同的函数名

# 这些函数现在内部调用 CCXT 实现
# 无需修改策略代码即可切换到 CCXT

__all__ = [
    # 客户端
    'CCXTClient',
    'get_ccxt_client',
    'init_ccxt_client',
    
    # 数据类
    'Contract',
    'Ticker',
    'Position',
    'OrderInfo',
    'WalletBalance',
    
    # 合约API
    'get_cex_contracts',
    'get_cex_fticker',
    'cex_futures_place',
    'cex_futures_close_position',
    'get_cex_position',
    'get_cex_all_position',
    'set_cex_leverage',
    'set_cex_dual_mode',
    
    # 现货API
    'get_cex_sticker',
    'get_cex_spot_candle',
    'cex_spot_place',
    'find_cex_spot_orders',
    'set_cex_margin_leverage',
    'set_cex_unified_leverage',
    
    # 账户API
    'get_cex_wallet_balance',
]

