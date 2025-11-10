"""
CCXT 交易所 API 封装模块

基于 CCXT 统一接口封装多交易所 API，支持合约交易、现货交易、账户管理和市场数据查询。

功能：
- 合约交易：开仓、平仓、查询持仓、设置杠杆
- 现货交易：买卖、查询订单、获取行情
- 账户管理：查询余额、设置杠杆
- 市场数据：K线、行情、交易对信息

支持的交易所：gate, bitget, okx, binance, bybit, huobi, kraken

配置方式（.env 文件）：
    EXCHANGE_ID=gate
    API_KEY=your_api_key
    API_SECRET=your_api_secret
    USE_TESTNET=false
    
    # Bitget 和 OKX 需要额外的 password/passphrase
    API_PASSWORD=your_passphrase  # 或使用 PASSPHRASE

交易对格式自动转换：统一使用 BTC_USDT 格式，自动转换为交易所特定格式。
"""

import os
import ccxt
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Contract:
    """永续合约信息"""
    name: str
    funding_rate: float
    funding_interval: int
    quanto_multiplier: float
    mark_price: float = 0.0
    index_price: float = 0.0
    
    def __post_init__(self):
        self.funding_interval = int(self.funding_interval)


@dataclass
class Ticker:
    """市场行情数据"""
    symbol: str
    last: float
    highest_bid: float
    lowest_ask: float
    base_volume: float
    quote_volume: float
    timestamp: int


@dataclass
class Position:
    """合约持仓信息"""
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
    side: str
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


SUPPORTED_EXCHANGES = {
    'gate': 'gate',
    'bitget': 'bitget',
    'okx': 'okx',
    'okex': 'okx',  # 别名
    'binance': 'binance',
    'bybit': 'bybit',
    'huobi': 'huobi',
    'kraken': 'kraken',
}

class CCXTClient:
    """CCXT 交易所客户端封装"""
    
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        password: str = None,
        use_testnet: bool = False,
        exchange_id: str = None
    ):
        """
        初始化 CCXT 客户端
        
        Args:
            api_key: API Key，未提供时从环境变量读取
            api_secret: API Secret，未提供时从环境变量读取
            password: API Password/Passphrase（Bitget/OKX 需要），未提供时从环境变量读取
            use_testnet: 是否使用测试网，未提供时从环境变量读取
            exchange_id: 交易所ID，未提供时从环境变量 EXCHANGE_ID 读取（默认 gate）
        
        环境变量优先级：
            1. 交易所特定配置：{EXCHANGE_ID}_API_KEY
            2. 通用配置：API_KEY
            3. 向后兼容：GATE_API_KEY
        
        注意：Bitget 和 OKX 需要额外的 password/passphrase 参数
        """
        # 从环境变量加载交易所ID（如果未提供）
        if exchange_id is None:
            exchange_id = os.getenv('EXCHANGE_ID', 'gate').lower()
        
        # 验证交易所是否支持
        if exchange_id not in SUPPORTED_EXCHANGES:
            # 尝试使用别名
            exchange_id = SUPPORTED_EXCHANGES.get(exchange_id, 'gate')
            if exchange_id not in SUPPORTED_EXCHANGES:
                logger.warning(f"不支持的交易所: {exchange_id}，使用默认值: gate")
                exchange_id = 'gate'
        
        self.exchange_id = exchange_id
        
        # 从环境变量加载配置（如果未提供）
        # 优先级：交易所特定配置 > 通用配置 > 向后兼容配置
        if api_key is None:
            # 1. 尝试交易所特定的环境变量
            exchange_specific_key = os.getenv(f'{exchange_id.upper()}_API_KEY', '')
            exchange_specific_secret = os.getenv(f'{exchange_id.upper()}_API_SECRET', '')
            exchange_specific_password = os.getenv(f'{exchange_id.upper()}_API_PASSWORD', '') or os.getenv(f'{exchange_id.upper()}_PASSPHRASE', '')
            
            # 2. 尝试通用环境变量（API_KEY, API_SECRET）
            generic_key = os.getenv('API_KEY', '')
            generic_secret = os.getenv('API_SECRET', '')
            generic_password = os.getenv('API_PASSWORD', '') or os.getenv('PASSPHRASE', '')
            
            # 3. 尝试向后兼容的环境变量（GATE_API_KEY）
            legacy_key = os.getenv('GATE_API_KEY', '')
            legacy_secret = os.getenv('GATE_API_SECRET', '')
            legacy_password = os.getenv('GATE_API_PASSWORD', '') or os.getenv('GATE_PASSPHRASE', '')
            
            # 按优先级选择
            self.api_key = (exchange_specific_key or generic_key or legacy_key)
            self.api_secret = (exchange_specific_secret or generic_secret or legacy_secret)
            self.api_password = (exchange_specific_password or generic_password or legacy_password)
        else:
            self.api_key = api_key
            self.api_secret = api_secret
            self.api_password = password or os.getenv('API_PASSWORD', '') or os.getenv('PASSPHRASE', '')

        # 测试网配置（支持交易所特定配置）
        if use_testnet is False:
            # 尝试交易所特定的测试网配置
            exchange_testnet = os.getenv(f'USE_TESTNET', '')
            if exchange_testnet:
                self.use_testnet = exchange_testnet.lower() == 'true'
            else:
                # 使用通用配置
                self.use_testnet = os.getenv('USE_TESTNET', 'false').lower() == 'true'
        else:
            self.use_testnet = use_testnet
        
        # 创建交易所实例
        try:
            exchange_class = getattr(ccxt, exchange_id)
        except AttributeError:
            raise ValueError(f"不支持的交易所: {exchange_id}。请确保已安装对应的 CCXT 版本")

        # 根据不同交易所配置选项
        exchange_options = {
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,  # 启用速率限制
            'timeout': 30000,  # 30秒超时
        }
        
        # Bitget 和 OKX 需要 password/passphrase
        if exchange_id in ['bitget', 'okx']:
            if self.api_password:
                exchange_options['password'] = self.api_password
            else:
                logger.warning(f"{exchange_id.upper()} 需要 API_PASSWORD 或 PASSPHRASE 参数，某些功能可能无法使用")
        
        # 交易所特定的配置
        if exchange_id in ['gate', 'bitget', 'okx', 'bybit']:
            exchange_options['options'] = {
                'defaultType': 'swap',  # 默认使用永续合约
                'defaultSettle': 'usdt',  # 默认USDT结算
            }
        elif exchange_id == 'binance':
            exchange_options['options'] = {
                'defaultType': 'future',  # Binance 使用 future
            }
        
        self.exchange = exchange_class(exchange_options)

        # 如果使用测试网
        if self.use_testnet:
            try:
                self.exchange.set_sandbox_mode(True)
                logger.info("CCXT 客户端已切换到测试网模式")
            except Exception as e:
                logger.warning(f"该交易所可能不支持测试网模式: {e}")
        
        # 验证 API 密钥（如果已配置）
        # if self.api_key and self.api_secret:
        #     try:
        #         # 尝试获取账户信息来验证 API 密钥
        #         test_balance = self.exchange.fetch_balance()
        #         logger.info(f"CCXT 客户端初始化完成 - 交易所: {exchange_id}, 测试网: {self.use_testnet}, API 密钥验证成功")
        #     except Exception as e:
        #         error_msg = str(e)
        #         if 'Invalid key' in error_msg or 'INVALID_KEY' in error_msg:
        #             logger.warning(f"API 密钥验证失败: 密钥无效或权限不足")
        #             logger.warning(f"提示：请检查 API 密钥是否正确，以及是否具有必要的交易权限")
        #         else:
        #             logger.warning(f"API 密钥验证时出现错误: {e}")
        #         logger.info(f"CCXT 客户端初始化完成 - 交易所: {exchange_id}, 测试网: {self.use_testnet}")
        # else:
        #     logger.info(f"CCXT 客户端初始化完成 - 交易所: {exchange_id}, 测试网: {self.use_testnet} (未配置 API 密钥)")
    
    def load_markets(self):
        """加载市场数据"""
        try:
            return self.exchange.load_markets()
        except Exception as e:
            logger.error(f"加载市场数据失败: {e}")
            return None


_ccxt_client: Optional[CCXTClient] = None


def get_ccxt_client() -> CCXTClient:
    """获取全局 CCXT 客户端实例（单例模式）"""
    global _ccxt_client
    if _ccxt_client is None:
        _ccxt_client = CCXTClient()
    return _ccxt_client


def init_ccxt_client(api_key: str = None, api_secret: str = None, password: str = None, use_testnet: bool = False) -> CCXTClient:
    """初始化 CCXT 客户端"""
    global _ccxt_client
    _ccxt_client = CCXTClient(api_key, api_secret, password, use_testnet)
    return _ccxt_client


def normalize_contract_name(contract: str, exchange_id: str = None, is_spot: bool = False) -> str:
    """
    将统一格式的合约名称转换为交易所特定格式
    
    Args:
        contract: 统一格式，如 "BTC_USDT"
        exchange_id: 交易所ID，None时从客户端获取
        is_spot: 是否为现货交易
    
    Returns:
        交易所特定的交易对格式
    """
    if exchange_id is None:
        client = get_ccxt_client()
        exchange_id = client.exchange_id
    
    # 统一格式: BTC_USDT
    if '_' in contract:
        base, quote = contract.split('_', 1)
    else:
        # 如果已经是其他格式，尝试解析
        base = contract.replace('USDT', '').replace('USD', '')
        quote = 'USDT'
    
    # 现货交易格式（大部分交易所都是 BTC/USDT）
    if is_spot:
        if exchange_id == 'huobi':
            return f"{base}-{quote}"
        else:
            return f"{base}/{quote}"
    
    # 合约交易格式
    if exchange_id in ['gate', 'bitget', 'okx', 'bybit']:
        # Gate.io, Bitget, OKX, Bybit: BTC/USDT:USDT
        return f"{base}/{quote}:USDT"
    elif exchange_id == 'binance':
        # Binance: BTC/USDT:USDT
        return f"{base}/{quote}:USDT"
    elif exchange_id == 'huobi':
        # Huobi: BTC-USDT
        return f"{base}-{quote}"
    else:
        # 默认格式
        return f"{base}/{quote}:USDT"


def denormalize_contract_name(symbol: str) -> str:
    """将交易所特定的交易对格式转换为统一格式（BTC_USDT）"""
    symbol = symbol.split(':')[0]
    return symbol.replace('/', '_').replace('-', '_')


def get_exchange_id() -> str:
    """获取当前使用的交易所ID"""
    client = get_ccxt_client()
    return client.exchange_id


def get_cex_contracts(contract: str = "") -> Optional[List[Contract]]:
    """获取永续合约列表"""
    try:
        client = get_ccxt_client()
        
        # 加载市场数据（带进度提示）
        logger.info("正在加载市场数据，这可能需要一些时间...")
        markets = client.exchange.load_markets()
        logger.info(f"已加载 {len(markets)} 个市场")
        
        contracts = []
        swap_markets = []
        
        for symbol, market in markets.items():
            if market.get('type') != 'swap' or market.get('settle') != 'USDT':
                continue
            
            if contract:
                if denormalize_contract_name(symbol) != contract:
                    continue
            
            swap_markets.append((symbol, market))
        
        logger.info(f"找到 {len(swap_markets)} 个 USDT 永续合约，正在获取资金费率...")
        
        for idx, (symbol, market) in enumerate(swap_markets):
            if idx > 0 and idx % 10 == 0:
                logger.info(f"已处理 {idx}/{len(swap_markets)} 个合约...")
            
            try:
                funding_rate_info = client.exchange.fetch_funding_rate(symbol)
                funding_rate = funding_rate_info.get('fundingRate', 0)
                
                funding_interval = 8 * 3600
                contract_size = market.get('contractSize', 1)
                quanto_multiplier = 1.0 / contract_size if contract_size > 0 else 1.0
                
                mark_price = market.get('info', {}).get('mark_price', 0)
                if not mark_price:
                    try:
                        ticker = client.exchange.fetch_ticker(symbol)
                        mark_price = ticker.get('last', 0)
                    except:
                        mark_price = 0
                
                contracts.append(Contract(
                    name=denormalize_contract_name(symbol),  # BTC/USDT:USDT -> BTC_USDT
                    funding_rate=funding_rate,
                    funding_interval=funding_interval,
                    quanto_multiplier=quanto_multiplier,
                    mark_price=mark_price
                ))
                
            except Exception as e:
                logger.debug(f"跳过合约 {symbol}: {e}")
                continue
        
        logger.info(f"成功获取 {len(contracts)} 个合约信息")
        return contracts if contracts else None
        
    except Exception as e:
        logger.error(f"获取合约列表失败: {e}", exc_info=True)
        return None


def get_cex_fticker(contract: str) -> Optional[List[Ticker]]:
    """获取合约行情"""
    try:
        client = get_ccxt_client()
        symbol = normalize_contract_name(contract, client.exchange_id)
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
        logger.error(f"获取合约行情失败 {contract}: {e}")
        return None


def cex_futures_place(contract: str, cost: float, price: str="0") -> Optional[OrderInfo]:
    """合约下单（按 USDT 成本下单，市价单）
    
    根据传入的 USDT 成本金额进行下单，不进行张数计算。
    对于 Bitget 等交易所，amount 参数直接表示 USDT 价值。
    
    Args:
        contract: 交易对名称（如 BTC_USDT）
        cost: USDT 成本金额，正数表示做多，负数表示做空
        price: 价格（未使用，保留兼容性）
    
    Returns:
        OrderInfo: 订单信息，失败返回 None
    """
    try:
        client = get_ccxt_client()
        symbol = normalize_contract_name(contract, client.exchange_id)
        
        # 判断方向：cost > 0 表示做多，cost < 0 表示做空
        side = 'buy' if cost > 0 else 'sell'
        cost_amount = abs(cost)
        
        if cost_amount <= 0:
            logger.error(f"成本金额无效: {cost_amount}，必须大于 0")
            return None
        
        order = None
        
        # 优先尝试使用 cost 参数（某些交易所支持）
        try:
            logger.info(f"尝试使用 cost 参数下单: {contract}, 成本={cost_amount} USDT, 方向={side}")
            order = client.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                cost=cost_amount,
                params={}
            )
            logger.info(f"使用 cost 参数下单成功: {contract}")
        except Exception as cost_error:
            error_msg = str(cost_error).lower()
            # 检查是否是 cost 参数不支持的错误
            if 'unexpected keyword argument' in error_msg and 'cost' in error_msg:
                logger.debug(f"交易所不支持 cost 参数，使用 amount 参数（USDT 价值）: {cost_error}")
                
                # 对于 Bitget 等交易所，amount 参数直接表示 USDT 价值（不是张数）
                # 对于 USDT 永续合约，amount 通常就是合约价值
                if client.exchange_id == 'bitget':
                    # Bitget 的 amount 就是 USDT 价值
                    logger.info(f"Bitget 按 USDT 价值下单: {contract}, 价值={cost_amount} USDT, 方向={side}")
                    order = client.exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=side,
                        amount=cost_amount,
                        params={}
                    )
                else:
                    # 其他交易所也尝试使用 amount（对于 USDT 永续合约，amount 通常也是价值）
                    logger.info(f"按 USDT 价值下单: {contract}, 价值={cost_amount} USDT, 方向={side}")
                    try:
                        order = client.exchange.create_order(
                            symbol=symbol,
                            type='market',
                            side=side,
                            amount=cost_amount,
                            params={}
                        )
                    except Exception as amount_error:
                        logger.error(f"使用 amount 参数下单也失败: {amount_error}")
                        raise amount_error
            else:
                # 其他类型的错误，直接抛出
                logger.error(f"使用 cost 参数下单失败: {cost_error}")
                raise cost_error
        
        # 检查订单是否成功创建
        if order is None:
            raise ValueError("订单创建失败，返回 None")
        
        if not isinstance(order, dict):
            raise ValueError(f"订单返回格式错误: {type(order)}")
        
        # 获取实际成交数量（对于按成本下单，这里可能是成交的合约价值或数量）
        filled_amount = order.get('filled', 0) or order.get('amount', 0)
        
        # 安全获取订单信息
        order_id = order.get('id', '')
        if not order_id:
            order_id = str(order.get('id', '')) if hasattr(order, 'get') else ''
        
        avg_price = order.get('average', 0) or order.get('price', 0)
        order_status = order.get('status', 'open')
        fee_info = order.get('fee', {})
        fee_cost = fee_info.get('cost', 0) if isinstance(fee_info, dict) else 0
        timestamp = order.get('timestamp', 0)
        
        logger.info(f"合约下单成功: {contract}, 订单ID={order_id}, 成交金额={filled_amount}, 均价={avg_price}")
        
        return OrderInfo(
            id=str(order_id),
            symbol=contract,
            side=side,
            amount=filled_amount,
            price=0,
            avg_deal_price=avg_price,
            status=order_status,
            fee=fee_cost,
            update_time_ms=timestamp
        )
        
    except Exception as e:
        logger.error(f"合约下单失败 {contract}: {e}", exc_info=True)
        return None


def cex_futures_close_position(contract: str) -> bool:
    """平掉合约仓位"""
    try:
        client = get_ccxt_client()
        
        # 转换合约名称格式为交易所特定格式
        symbol = normalize_contract_name(contract, client.exchange_id)
        
        # 获取当前持仓
        try:
            positions = client.exchange.fetch_positions([symbol])
        except Exception as pos_error:
            # 如果获取持仓失败，尝试获取所有持仓
            logger.debug(f"获取指定合约持仓失败，尝试获取所有持仓: {pos_error}")
            try:
                positions = client.exchange.fetch_positions()
                # 过滤出指定合约的持仓
                positions = [p for p in positions if isinstance(p, dict) and p.get('symbol') == symbol]
            except Exception as all_pos_error:
                logger.warning(f"获取持仓失败: {all_pos_error}")
                positions = []
        
        if not positions:
            logger.debug(f"未找到 {contract} 的持仓，可能已经平仓或未开仓")
            return True  # 没有持仓也算成功
        
        has_position = False
        for position in positions:
            if not isinstance(position, dict):
                continue
            
            contracts = position.get('contracts', 0)
            if contracts == 0 or abs(float(contracts)) < 0.0001:
                continue
            
            has_position = True
            
            # 平仓：反向操作
            side = 'sell' if contracts > 0 else 'buy'
            amount = abs(float(contracts))
            
            # 减仓参数
            params = {'reduceOnly': True}
            
            # 对于 Bitget，可能需要特殊处理
            if client.exchange_id == 'bitget':
                # Bitget 可能需要使用 close_position 方法
                try:
                    client.exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=side,
                        amount=amount,
                        params=params
                    )
                except Exception as bitget_error:
                    error_msg = str(bitget_error).lower()
                    if 'no position' in error_msg or '22002' in str(bitget_error):
                        logger.debug(f"Bitget 提示无持仓，可能已经平仓: {bitget_error}")
                        return True
                    else:
                        raise bitget_error
            else:
                client.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=amount,
                    params=params
                )
            
            logger.info(f"平仓成功: {contract}, 数量: {amount}")
            return True
        
        if not has_position:
            logger.debug(f"{contract} 没有有效持仓（持仓数量为0）")
            return True  # 没有持仓也算成功
        
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        # 如果是"无持仓"错误，视为成功
        if 'no position' in error_msg or '22002' in str(e):
            logger.debug(f"平仓时提示无持仓，可能已经平仓: {e}")
            return True
        logger.error(f"平仓失败 {contract}: {e}")
        return False


def get_cex_position(contract: str) -> Optional[Position]:
    """获取合约持仓"""
    try:
        client = get_ccxt_client()
        
        # 转换合约名称格式为交易所特定格式
        symbol = normalize_contract_name(contract, client.exchange_id)
        
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
        logger.error(f"获取持仓失败 {contract}: {e}")
        return None


def get_cex_all_position() -> Optional[List[Position]]:
    """获取所有合约持仓"""
    try:
        client = get_ccxt_client()
        
        positions = client.exchange.fetch_positions()
        
        result = []
        for position in positions:
            contracts = position.get('contracts', 0)
            if contracts == 0:
                continue
            
            symbol = position.get('symbol', '')
            # 转换格式为统一格式
            contract_name = denormalize_contract_name(symbol)
            
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
        logger.error(f"获取所有持仓失败: {e}")
        return None


def set_cex_leverage(contract: str, leverage: str) -> bool:
    """设置合约杠杆"""
    try:
        client = get_ccxt_client()
        
        # 转换合约名称格式为交易所特定格式
        symbol = normalize_contract_name(contract, client.exchange_id)
        
        client.exchange.set_leverage(int(leverage), symbol)
        logger.info(f"设置杠杆成功: {contract} -> {leverage}x")
        return True
        
    except Exception as e:
        logger.error(f"设置杠杆失败 {contract}: {e}")
        return False


def set_cex_dual_mode(dual_mode: bool) -> bool:
    """设置持仓模式（True=双向，False=单向）"""
    try:
        client = get_ccxt_client()
        
        # 检查 API 密钥是否配置
        if not client.api_key or not client.api_secret:
            logger.warning("API 密钥未配置，无法设置持仓模式")
            return False
        
        # 对于 Gate.io，持仓模式设置可能需要特定权限
        # 如果设置失败，不影响策略运行（策略使用单向持仓模式）
        try:
            # 尝试使用 CCXT 标准方法
            client.exchange.set_position_mode(hedged=dual_mode)
            logger.info(f"设置持仓模式: {'双向' if dual_mode else '单向'}")
            return True
        except Exception as e:
            error_msg = str(e)
            
            # 检查是否是 API 密钥错误
            if 'Invalid key' in error_msg or 'INVALID_KEY' in error_msg:
                logger.warning(f"API 密钥无效或权限不足，无法设置持仓模式")
                logger.warning(f"提示：请检查 API 密钥是否正确，以及是否具有合约交易权限")
                logger.warning(f"策略将继续运行（Gate.io 默认使用单向持仓模式）")
            elif 'not supported' in error_msg.lower() or 'unsupported' in error_msg.lower():
                logger.warning(f"该交易所不支持设置持仓模式: {e}")
            else:
                logger.warning(f"设置持仓模式失败: {e}")
            
            # 对于 Gate.io，如果设置失败，默认使用单向模式（不影响策略）
            if not dual_mode:
                logger.info("策略使用单向持仓模式，无需额外设置")
                return True
            
            return False
        
    except Exception as e:
        logger.warning(f"设置持仓模式时发生错误: {e}")
        return False


def get_cex_sticker(contract: str) -> Optional[List[Ticker]]:
    """获取现货行情"""
    try:
        client = get_ccxt_client()
        
        # 转换格式为交易所特定格式（现货）
        symbol = normalize_contract_name(contract, client.exchange_id, is_spot=True)
        
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
        logger.error(f"获取现货行情失败 {contract}: {e}")
        return None


def get_cex_spot_candle(contract: str, interval: str = "1m", limit: int = 100) -> Optional[list]:
    """获取现货K线数据"""
    try:
        client = get_ccxt_client()
        
        # 转换格式为交易所特定格式（现货）
        symbol = normalize_contract_name(contract, client.exchange_id, is_spot=True)
        
        # 获取OHLCV数据
        ohlcv = client.exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
        
        return ohlcv if ohlcv else None
        
    except Exception as e:
        logger.error(f"获取K线数据失败 {contract}: {e}")
        return None


def cex_spot_place(contract: str, side: str, cost: str, size: str) -> Optional[OrderInfo]:
    """现货杠杆下单（按 USDT 成本下单，市价单）
    
    支持现货杠杆交易，买入和卖出都按 USDT 成本金额执行：
    - 买入（做多）：花费 cost USDT 买入对应价值的币（使用杠杆）
    - 卖出（做空）：卖出价值 cost USDT 的币（使用杠杆做空）
    
    Args:
        contract: 交易对名称（如 BTC_USDT）
        side: 交易方向，'buy'（做多）或 'sell'（做空）
        cost: USDT 成本金额（字符串格式）
    
    Returns:
        OrderInfo: 订单信息，失败返回 None
    """
    try:
        client = get_ccxt_client()
        
        # 转换格式为交易所特定格式（现货杠杆使用 margin 市场类型）
        symbol = normalize_contract_name(contract, client.exchange_id, is_spot=True)
        
        cost_amount = f'{float(cost):.2f}'
        
        # 验证成本金额
        if cost_amount <= 0:
            logger.error(f"成本金额无效: {cost_amount}，必须大于 0")
            return None
        
        # 现货杠杆交易参数
        params = {
            'loanType': "autoLoanAndRepay",
            'marginMode': 'crossed', # 使用逐仓模式
        }
        
        # Bitget 需要 marginCoin 参数（保证金币种）
        if client.exchange_id == 'bitget':
            if '_' in contract:
                _, quote = contract.split('_', 1)
                params['marginCoin'] = quote
            elif '/' in symbol:
                _, quote = symbol.split('/', 1)
                params['marginCoin'] = quote
            else:
                params['marginCoin'] = 'USDT'
        
        order = None
        filled_amount = cost_amount
        
        # 获取当前价格（买入和卖出都需要根据价格计算数量）
        ticker = client.exchange.fetch_ticker(symbol)
        if not ticker or not isinstance(ticker, dict):
            raise ValueError(f"无法获取 {contract} 的行情数据")
        
        if side == 'buy':
            params["quoteSize"]= cost_amount
            # 买入（做多）：按成本买入
            # 对于 Bitget 现货杠杆，需要特殊处理
            if client.exchange_id == 'bitget':
                order = client.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=cost_amount,
                    params=params
                )

        else:
            params["baseSize"] = size
            # 使用杠杆参数下单（做空需要杠杆支持）
            order = client.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=size,
                params=params,
            )

        if order is None:
            raise ValueError("订单创建失败，返回 None")
        
        if not isinstance(order, dict):
            raise ValueError(f"订单返回格式错误: {type(order)}")
        
        # 如果 filled_amount 为 0，尝试从订单中获取实际成交数量
        if filled_amount == 0:
            filled_amount = order.get('filled', 0) or order.get('amount', 0)
        
        # 安全获取订单信息
        order_id = order.get('id', '')
        if not order_id:
            order_id = str(order.get('id', '')) if hasattr(order, 'get') else ''
        
        avg_price = order.get('average', 0) or order.get('price', 0)
        order_status = order.get('status', 'open')
        fee_info = order.get('fee', {})
        fee_cost = fee_info.get('cost', 0) if isinstance(fee_info, dict) else 0
        timestamp = order.get('timestamp', 0)
        
        logger.info(f"现货杠杆下单成功: {contract}, 方向={side}, 订单ID={order_id}, 成交数量={filled_amount}, 均价={avg_price}")
        
        return OrderInfo(
            id=str(order_id),
            symbol=contract,
            side=side,
            amount=filled_amount,
            price=0,
            avg_deal_price=avg_price,
            status=order_status,
            fee=fee_cost,
            update_time_ms=timestamp
        )
        
    except Exception as e:
        logger.error(f"现货杠杆下单失败 {contract}: {e}", exc_info=True)
        return None


def cex_spot_close_position(contract: str) -> bool:
    """现货杠杆平仓
    
    查询现货杠杆持仓并进行反向交易平仓：
    - 做多持仓（买入的币）：卖出平仓
    - 做空持仓（借币卖出的）：买入平仓
    
    Args:
        contract: 交易对名称（如 BTC_USDT）
    
    Returns:
        bool: 平仓成功返回 True，失败返回 False
    """
    try:
        client = get_ccxt_client()
        
        # 转换格式为交易所特定格式（现货）
        symbol = normalize_contract_name(contract, client.exchange_id, is_spot=True)
        
        # 现货杠杆平仓参数
        params = {
            'marginMode': 'isolated',  # 使用逐仓模式
            'createMarketBuyOrderRequiresPrice': False
        }
        
        # Bitget 需要 marginCoin 参数
        if client.exchange_id == 'bitget':
            if '_' in contract:
                _, quote = contract.split('_', 1)
                params['marginCoin'] = quote
            elif '/' in symbol:
                _, quote = symbol.split('/', 1)
                params['marginCoin'] = quote
            else:
                params['marginCoin'] = 'USDT'
        
        # 获取现货杠杆持仓
        # 注意：某些交易所可能需要使用 fetch_balance 或 fetch_positions 来获取杠杆持仓
        positions = []
        try:
            # 尝试获取 margin 持仓
            positions = client.exchange.fetch_positions([symbol])
            # 过滤出 margin 持仓
            positions = [p for p in positions if isinstance(p, dict) and 
                        (p.get('marginMode') == 'isolated' or p.get('type') == 'margin')]
        except Exception as pos_error:
            logger.debug(f"通过 fetch_positions 获取现货杠杆持仓失败，尝试其他方式: {pos_error}")
            # 某些交易所可能需要通过 fetch_balance 获取杠杆余额
            try:
                balance = client.exchange.fetch_balance({'type': 'margin'})
                if balance and isinstance(balance, dict):
                    # 从余额中提取持仓信息
                    base_currency = symbol.split('/')[0] if '/' in symbol else contract.split('_')[0]
                    if base_currency in balance:
                        base_balance = balance[base_currency]
                        if isinstance(base_balance, dict):
                            borrowed = base_balance.get('borrowed', 0) or 0
                            free = base_balance.get('free', 0) or 0
                            used = base_balance.get('used', 0) or 0
                            
                            # 如果有借币（做空）或持仓（做多），需要平仓
                            if borrowed > 0 or (free > 0 and used > 0):
                                # 构造持仓信息
                                if borrowed > 0:
                                    # 做空持仓：借币卖出，需要买入还币
                                    positions.append({
                                        'symbol': symbol,
                                        'side': 'short',
                                        'contracts': borrowed,
                                        'marginMode': 'isolated'
                                    })
                                if free > 0:
                                    # 做多持仓：买入的币，需要卖出平仓
                                    positions.append({
                                        'symbol': symbol,
                                        'side': 'long',
                                        'contracts': free,
                                        'marginMode': 'isolated'
                                    })
            except Exception as balance_error:
                logger.debug(f"通过 fetch_balance 获取现货杠杆持仓也失败: {balance_error}")
        
        if not positions:
            logger.debug(f"未找到 {contract} 的现货杠杆持仓，可能已经平仓或未开仓")
            return True  # 没有持仓也算成功
        
        has_position = False
        for position in positions:
            if not isinstance(position, dict):
                continue
            
            # 获取持仓数量
            contracts = position.get('contracts', 0)
            if contracts == 0 or abs(float(contracts)) < 0.0001:
                continue
            
            has_position = True
            position_side = position.get('side', '')
            contracts_float = float(contracts)
            
            # 确定平仓方向
            # 做多持仓（买入的币）：需要卖出平仓
            # 做空持仓（借币卖出的）：需要买入还币平仓
            if position_side == 'long' or contracts_float > 0:
                # 做多持仓，卖出平仓
                side = 'sell'
                amount = abs(contracts_float)
            else:
                # 做空持仓，买入还币平仓
                side = 'buy'
                amount = abs(contracts_float)
            
            logger.info(f"现货杠杆平仓: {contract}, 方向={position_side}, 数量={amount}, 平仓操作={side}")
            
            # 获取当前价格以计算买入成本（如果是买入还币）
            if side == 'buy':
                ticker = client.exchange.fetch_ticker(symbol)
                if not ticker or not isinstance(ticker, dict):
                    raise ValueError(f"无法获取 {contract} 的行情数据")
                
                current_price = ticker.get('ask', 0) or ticker.get('last', 0) or ticker.get('bid', 0)
                if current_price <= 0:
                    raise ValueError(f"无法获取 {contract} 的有效价格")
                
                # 计算买入成本（稍微多买一点以确保还币）
                buy_cost = amount * current_price * 1.01
                
                # 尝试使用 cost 参数买入
                try:
                    order = client.exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=side,
                        cost=buy_cost,
                        params=params
                    )
                    logger.info(f"使用 cost 参数买入还币成功: {contract}, 成本={buy_cost} USDT")
                except Exception as cost_error:
                    error_msg = str(cost_error).lower()
                    if 'unexpected keyword argument' in error_msg and 'cost' in error_msg:
                        # 不支持 cost 参数，使用 amount
                        order = client.exchange.create_order(
                            symbol=symbol,
                            type='market',
                            side=side,
                            amount=amount * 1.01,  # 稍微多买一点
                            params=params
                        )
                    else:
                        raise cost_error
            else:
                # 卖出平仓
                order = client.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=amount,
                    params=params
                )
            
            logger.info(f"现货杠杆平仓成功: {contract}, 方向={position_side}, 数量={amount}")
        
        if not has_position:
            logger.debug(f"{contract} 没有有效的现货杠杆持仓（持仓数量为0）")
            return True  # 没有持仓也算成功
        
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        if 'no position' in error_msg or 'no margin position' in error_msg:
            logger.debug(f"现货杠杆平仓时提示无持仓，可能已经平仓: {e}")
            return True  # 无持仓也算成功
        else:
            logger.error(f"现货杠杆平仓失败 {contract}: {e}", exc_info=True)
            return False


def find_cex_spot_orders(contract: str) -> Optional[List[OrderInfo]]:
    """查询现货订单历史（优先返回已完成的订单，如果没有则返回开放订单）"""
    try:
        client = get_ccxt_client()
        symbol = normalize_contract_name(contract, client.exchange_id, is_spot=True)
        
        all_orders = []
        closed_orders = []
        open_orders = []
        
        # 对于 Bitget，尝试多种方式获取订单
        if client.exchange_id == 'bitget':
            # 1. 尝试获取已完成的订单
            try:
                closed_orders = client.exchange.fetch_closed_orders(symbol, limit=50)
                logger.debug(f"Bitget 获取到 {len(closed_orders) if closed_orders else 0} 个已完成订单")
            except Exception as closed_error:
                logger.debug(f"Bitget fetch_closed_orders 失败: {closed_error}")
            
            # 2. 尝试获取开放订单
            try:
                open_orders = client.exchange.fetch_open_orders(symbol, limit=50)
                logger.debug(f"Bitget 获取到 {len(open_orders) if open_orders else 0} 个开放订单")
            except Exception as open_error:
                logger.debug(f"Bitget fetch_open_orders 失败: {open_error}")
            
            # 合并所有订单
            all_orders = []
            if closed_orders:
                all_orders.extend(closed_orders)
            if open_orders:
                all_orders.extend(open_orders)
        else:
            # 其他交易所：尝试使用 fetch_orders，如果不支持则使用 fetchClosedOrders + fetchOpenOrders
            try:
                all_orders = client.exchange.fetch_orders(symbol, limit=50)
            except Exception as fetch_orders_error:
                error_msg = str(fetch_orders_error).lower()
                if 'not supported' in error_msg or 'fetchorders' in error_msg.lower():
                    # 如果不支持 fetch_orders，分别获取已完成和开放订单
                    logger.debug(f"交易所不支持 fetch_orders，分别获取已完成和开放订单: {fetch_orders_error}")
                    try:
                        closed_orders = client.exchange.fetch_closed_orders(symbol, limit=50)
                        if closed_orders:
                            all_orders.extend(closed_orders)
                    except Exception as closed_error:
                        logger.debug(f"fetch_closed_orders 失败: {closed_error}")
                    
                    try:
                        open_orders = client.exchange.fetch_open_orders(symbol, limit=50)
                        if open_orders:
                            all_orders.extend(open_orders)
                    except Exception as open_error:
                        logger.debug(f"fetch_open_orders 失败: {open_error}")
                else:
                    raise fetch_orders_error
        
        if not all_orders:
            logger.debug(f"未找到 {contract} 的现货订单（已完成和开放订单都没有）")
            return None
        
        result = []
        for order in all_orders:
            if not isinstance(order, dict):
                continue
            
            # CCXT 订单状态：'open', 'closed', 'canceled', 'filled'
            order_status = order.get('status', '')
            
            # 优先返回已完成的订单，如果没有则返回开放订单
            if order_status not in ['closed', 'filled', 'open']:
                continue
            
            # 安全获取订单信息
            order_id = order.get('id', '')
            order_side = order.get('side', '')
            order_amount = order.get('amount', 0)
            order_price = order.get('price', 0)
            avg_price = order.get('average', 0) or order_price
            fee_info = order.get('fee', {})
            fee_cost = fee_info.get('cost', 0) if isinstance(fee_info, dict) else 0
            timestamp = order.get('timestamp', 0)
            
            # 统一状态：已完成订单为 'closed'，开放订单保持 'open'
            final_status = 'closed' if order_status in ['closed', 'filled'] else 'open'
            
            result.append(OrderInfo(
                id=str(order_id),
                symbol=contract,
                side=order_side,
                amount=order_amount,
                price=order_price,
                avg_deal_price=avg_price,
                status=final_status,
                fee=fee_cost,
                update_time_ms=timestamp
            ))
        
        # 按时间排序，最新的在前
        result.sort(key=lambda x: x.update_time_ms, reverse=True)
        
        if result:
            closed_count = sum(1 for o in result if o.status == 'closed')
            open_count = sum(1 for o in result if o.status == 'open')
            logger.debug(f"找到 {len(result)} 个现货订单: {contract}（已完成: {closed_count}, 开放: {open_count}）")
        else:
            logger.debug(f"未找到有效的现货订单: {contract}（原始订单数: {len(all_orders)}）")
        
        return result if result else None
        
    except Exception as e:
        logger.error(f"查询订单失败 {contract}: {e}", exc_info=True)
        return None


def set_cex_margin_leverage(contract: str, leverage: str) -> bool:
    """设置现货杠杆（逐仓）"""
    try:
        client = get_ccxt_client()
        
        # 转换格式为交易所特定格式（现货）
        symbol = normalize_contract_name(contract, client.exchange_id, is_spot=True)
        
        # 准备参数
        params = {'marginMode': 'isolated'}
        
        # Bitget 需要 marginCoin 参数（保证金币种）
        if client.exchange_id == 'bitget':
            # 从合约名称中提取 quote currency（如 ETH_USDT -> USDT）
            if '_' in contract:
                _, quote = contract.split('_', 1)
                params['marginCoin'] = quote
            else:
                # 如果格式不对，尝试从 symbol 中提取
                if '/' in symbol:
                    _, quote = symbol.split('/', 1)
                    params['marginCoin'] = quote
                else:
                    logger.warning(f"无法从 {contract} 提取 margin coin，使用默认值 USDT")
                    params['marginCoin'] = 'USDT'
        
        # 某些交易所支持设置保证金杠杆
        client.exchange.set_leverage(int(leverage), symbol, params=params)
        logger.info(f"设置现货杠杆成功: {contract} -> {leverage}x")
        return True
        
    except Exception as e:
        logger.warning(f"设置现货杠杆失败（可能不支持）{contract}: {e}")
        return False


def set_cex_unified_leverage(currency: str, leverage: str) -> bool:
    """设置统一账户杠杆"""
    try:
        client = get_ccxt_client()
        if client.exchange_id == 'gate':
            logger.warning(f"统一账户杠杆设置在 CCXT 中可能不直接支持")
            return True
        return True
    except Exception as e:
        logger.error(f"设置统一账户杠杆失败 {currency}: {e}")
        return False


def get_cex_wallet_balance() -> Optional[WalletBalance]:
    """获取钱包余额"""
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
        logger.error(f"获取钱包余额失败: {e}")
        return None

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

