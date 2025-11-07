"""
Gate.io 交易所 REST API 封装模块

============================================================
模块功能
============================================================
本模块封装了 Gate.io 交易所的 REST API，提供以下功能：

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
使用说明
============================================================
1. 配置 API 密钥：修改 config 中的 key 和 secret
2. 选择环境：正式环境或测试网
3. 调用相应函数进行交易操作

============================================================
API 文档
============================================================
官方文档: https://www.gate.io/docs/developers/apiv4/zh_CN/
"""

import logging
from gate_api.exceptions import GateApiException

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 导入 Gate.io SDK ====================
from gate_api import FuturesOrder, Order, UnifiedLeverageSetting, MarginMarketLeverage

# ==================== 导入 API 客户端管理器 ====================
from .api_client import get_api_clients

# ==================== 初始化 API 客户端 ====================
# 使用客户端管理器获取所有 API 实例
# 优点：
# 1. 配置集中管理，便于维护
# 2. 支持从环境变量加载配置
# 3. 支持单例模式，避免重复创建
# 4. API 密钥不再硬编码，更安全
#
# 配置方式：
# 方式1：使用默认配置（当前方式）
#     clients = get_api_clients()
#
# 方式2：使用自定义配置
#     clients = get_api_clients(
#         api_key='your_key',
#         api_secret='your_secret',
#         use_testnet=False  # 正式环境
#     )
#
# 方式3：从环境变量加载
#     export GATE_API_KEY="your_key"
#     export GATE_API_SECRET="your_secret"
#     export GATE_USE_TESTNET="false"
#     from rest.api_client import init_api_client_from_env
#     clients = init_api_client_from_env()

clients = get_api_clients(use_testnet=True, settle="usdt")

# 提取各个 API 实例
margin_api = clients['margin_api']      # 保证金/杠杆交易API
spot_api = clients['spot_api']          # 现货交易API
unified_api = clients['unified_api']    # 统一账户API
futures_api = clients['futures_api']    # 合约交易API
wallet_api = clients['wallet_api']      # 钱包API
settle = clients['settle']              # 结算货币

# ==================== 合约查询相关 ====================

def get_cex_contracts():
    """
    获取所有 USDT 结算的永续合约列表
    
    功能：
    - 查询交易所所有可用的永续合约
    - 包含合约名称、资金费率、合约乘数等信息
    
    Returns:
        list[Contract]: 合约列表，包含以下关键字段：
            - name: 合约名称，如 "BTC_USDT"
            - funding_rate: 当前资金费率
            - funding_interval: 资金费率结算间隔（秒）
            - quanto_multiplier: 合约乘数
        失败时返回 None
    
    异常处理：
        捕获所有异常并记录日志，返回 None
    """
    try:
        return futures_api.list_futures_contracts("usdt")
    except Exception as e:
        logger.error(f"获取合约列表失败: {e}")
        return None


# ==================== 账户查询相关 ====================

def get_cex_wallet_balance():
    """
    获取账户总资产余额
    
    功能：
    - 查询用户在交易所的总资产
    - 包含现货、合约、杠杆等所有账户的余额
    
    Returns:
        TotalBalance: 总资产对象，包含以下关键字段：
            - details: 各账户余额详情
                - spot: 现货账户
                - futures: 合约账户
                - margin: 杠杆账户
            - total: 总资产（等值）
        失败时返回 None
    
    应用场景：
        在开仓前检查账户余额是否充足
    """
    try:
        return wallet_api.get_total_balance()
    except Exception as e:
        logger.error(f"获取钱包余额失败: {e}")
        return None


# ==================== 合约交易相关 ====================

def cex_futures_close_position(contract: str):
    """
    平掉指定合约的所有持仓（市价全平）
    
    功能：
    - 使用市价单平掉指定合约的全部持仓
    - 无论多空方向，一键平仓
    
    Args:
        contract (str): 合约名称，如 "BTC_USDT"
    
    Returns:
        FuturesOrder: 平仓订单对象，包含订单ID、成交信息等
        失败时返回 None
    
    订单参数说明：
        - size=0: 平仓数量为0（系统自动平掉全部持仓）
        - price="0": 市价单
        - close=True: 标记为平仓操作
        - tif='ioc': 立即成交或取消（Immediate or Cancel）
    
    应用场景：
        策略止损、止盈、或紧急平仓时使用
    """
    try:
        order = FuturesOrder(contract=contract, size=0, price="0", close=True, tif='ioc')
        return futures_api.create_futures_order(settle, order)
    except Exception as e:
        logger.error(f"合约平仓失败 contract={contract}, error={e}")
        return None


def cex_futures_place(contract: str, price: str, size: int):
    """
    合约开仓/加仓（支持市价和限价）
    
    功能：
    - 开多：size > 0
    - 开空：size < 0
    - 支持市价单和限价单
    
    Args:
        contract (str): 合约名称，如 "BTC_USDT"
        price (str): 价格
            - "0" 或 "": 市价单
            - 其他: 限价单价格
        size (int): 合约张数
            - 正数：开多/加多
            - 负数：开空/加空
    
    Returns:
        FuturesOrder: 订单对象，包含以下关键字段：
            - id: 订单ID
            - status: 订单状态
            - size: 成交数量
        失败时返回 None
    
    订单类型（Time in Force）：
        - ioc: 立即成交或取消（市价单）
        - gtc: 一直有效直到取消（限价单，Good Till Cancelled）
    
    订单参数说明：
        - iceberg=0: 不使用冰山委托
    
    应用场景：
        策略开仓、加仓时使用
    """
    try:
        # 根据价格判断订单类型
        tif = 'gtc'
        if price == '0' or price == '':
            tif = 'ioc'  # 市价单：立即成交或取消
        else:
            tif = 'gtc'  # 限价单：一直有效

        order = FuturesOrder(contract=contract, size=size, price=price, tif=tif, iceberg=0)
        return futures_api.create_futures_order(settle, order)
    except Exception as e:
        logger.error(f"合约下单失败 contract={contract}, price={price}, size={size}, error={e}")
        return None


# ==================== 现货交易相关 ====================

def cex_spot_place(currency_pair: str, side: str, amount: str, price="0"):
    """
    现货下单（支持统一账户杠杆交易）
    
    功能：
    - 支持市价单和限价单
    - 自动借币/借U（auto_borrow）
    - 自动还币/还U（auto_repay）
    - 使用统一账户（unified account）
    
    Args:
        currency_pair (str): 交易对，如 "BTC_USDT"
        side (str): 买卖方向
            - "buy": 买入（做多）
            - "sell": 卖出（做空）
        amount (str): 交易数量
            - buy时：金额（USDT）
            - sell时：数量（币）
        price (str, optional): 价格，默认 "0"
            - "0" 或 "": 市价单
            - 其他: 限价单价格
    
    Returns:
        Order: 订单对象，包含以下关键字段：
            - id: 订单ID
            - status: 订单状态
            - avg_deal_price: 平均成交价
            - amount: 交易数量
            - fee: 手续费
        失败时返回 None
    
    订单类型：
        1. 市价单（Market Order）
           - type="market"
           - time_in_force='ioc': 立即成交或取消
           - 无需指定价格
        
        2. 限价单（Limit Order）
           - type="limit"
           - time_in_force='gtc': 一直有效直到取消
           - 需要指定价格
    
    账户参数：
        - account="unified": 使用统一账户
        - auto_borrow=True: 自动借币（余额不足时）
        - auto_repay=True: 自动还币（卖出时优先还借币）
    
    应用场景：
        资金费率套利中的现货对冲操作
    
    API 文档：
        https://www.gate.io/docs/developers/apiv4/zh_CN/#%E4%B8%8B%E5%8D%95
    """
    try:
        # 判断是市价单还是限价单
        is_market_order = (price == '0' or price == '' or price == 0)
        
        if is_market_order:
            # ========== 市价单配置 ==========
            # 市价单立即按照市场最优价格成交
            order = Order(
                currency_pair=currency_pair,  # 交易对
                type="market",                # 市价单
                time_in_force='ioc',          # 立即成交或取消
                side=side,                    # 买卖方向
                amount=amount,                # 交易数量
                account="unified",            # 统一账户
                auto_borrow=True,             # 自动借币
                auto_repay=True               # 自动还币
            )
        else:
            # ========== 限价单配置 ==========
            # 限价单按照指定价格挂单，等待成交
            order = Order(
                currency_pair=currency_pair,  # 交易对
                type="limit",                 # 限价单
                side=side,                    # 买卖方向
                amount=amount,                # 交易数量
                price=str(price),             # 限价价格
                time_in_force='gtc',          # 一直有效
                account="unified",            # 统一账户
                auto_borrow=True,             # 自动借币
                auto_repay=True               # 自动还币
            )
        
        return spot_api.create_order(order)
    
    except GateApiException as e:
        # Gate.io API 异常，包含详细的错误信息
        logger.error(f"现货下单失败 currency_pair={currency_pair}, side={side}, price={price}, amount={amount}, error={e}")
        logger.error(f"详细错误: {e.label}: {e.message}")
        if hasattr(e, 'body') and e.body:
            logger.error(f"响应体: {e.body}")
        return None
    except Exception as e:
        # 其他异常
        logger.error(f"现货下单异常 currency_pair={currency_pair}, side={side}, price={price}, amount={amount}, error={e}")
        return None


def cex_close_position(contract: str, auto_size: str, price="0"):
    """
    合约平仓（减仓模式）
    
    功能：
    - 平掉指定方向和数量的仓位
    - 支持市价和限价平仓
    - 只减仓，不会开反向仓位
    
    Args:
        contract (str): 合约名称，如 "BTC_USDT"
        auto_size (str): 自动平仓方向
            - "close_long": 平多仓
            - "close_short": 平空仓
        price (str, optional): 价格，默认 "0"
            - "0": 市价平仓
            - 其他: 限价平仓价格
    
    Returns:
        FuturesOrder: 平仓订单对象
        失败时返回 None
    
    订单参数说明：
        - size=0: 数量为0，由 auto_size 控制实际平仓方向和数量
        - reduce_only=True: 只减仓，不开反向仓位
        - close=False: 不是全平仓（而是部分平仓）
    
    注意事项：
        与 cex_futures_close_position 的区别：
        - cex_futures_close_position: 全平仓（close=True）
        - cex_close_position: 可控制平仓方向和数量（auto_size）
    """
    try:
        # 根据价格判断订单类型
        tif = 'gtc'
        if price == "0":
            tif = 'ioc'  # 市价：立即成交或取消
            price = 0
        else:
            tif = 'gtc'  # 限价：一直有效

        order = FuturesOrder(
            contract=contract,      # 合约名称
            size=0,                 # 数量由 auto_size 控制
            price=price,            # 平仓价格
            auto_size=auto_size,    # 自动平仓方向
            reduce_only=True,       # 只减仓
            close=False,            # 不是全平仓
            tif=tif                 # 订单类型
        )
        return futures_api.create_futures_order(settle, order)
    except Exception as e:
        logger.error(f"获取平仓订单失败 contract={contract}, auto_size={auto_size}, price={price}, error={e}")
        return None


# ==================== 杠杆配置相关 ====================

def get_cex_unified_leverage(contract: str):
    """
    获取统一账户币种杠杆配置信息
    
    功能：
    - 查询指定币种的杠杆配置
    - 获取最大、最小可设置杠杆倍数
    
    Args:
        contract (str): 币种名称，如 "BTC"
    
    Returns:
        tuple: (响应数据, 状态码, 响应头)
            响应数据包含：
            - max_leverage: 最大杠杆倍数
            - min_leverage: 最小杠杆倍数
            - leverage: 当前杠杆倍数
        失败时返回 None
    
    应用场景：
        在设置杠杆前，先查询允许的杠杆范围
    """
    try:
        return unified_api.get_user_leverage_currency_config_with_http_info(contract)
    except Exception as e:
        logger.error(f"获取统一杠杆配置失败 contract={contract}, error={e}")
        return None


def set_cex_unified_leverage(currency: str, leverage: str):
    """
    设置统一账户币种杠杆倍数
    
    功能：
    - 为指定币种设置杠杆倍数
    - 用于现货杠杆交易（借币做多/做空）
    
    Args:
        currency (str): 币种名称，如 "BTC"
        leverage (str): 杠杆倍数，如 "2"、"3"、"5" 等
    
    Returns:
        tuple: (响应数据, 状态码, 响应头)
        失败时返回 None
    
    注意事项：
        - 杠杆倍数必须在交易所允许的范围内
        - 不同币种的最大杠杆倍数可能不同
        - 建议先调用 get_cex_unified_leverage 查询允许范围
    
    应用场景：
        资金费率套利中，设置现货杠杆用于借币操作
    """
    try:
        lever_setting = UnifiedLeverageSetting(
            currency=currency,
            leverage=leverage
        )
        return unified_api.set_user_leverage_currency_setting_with_http_info(lever_setting)
    except Exception as e:
        logger.error(f"设置统一杠杆失败 currency={currency}, leverage={leverage}, error={e}")
        return None


def set_cex_margin_leverage(currency: str, leverage: str):
    """
    设置保证金账户交易对杠杆倍数
    
    功能：
    - 为指定交易对设置保证金杠杆
    - 用于借贷交易
    
    Args:
        currency (str): 交易对，如 "BTC_USDT"
        leverage (str): 杠杆倍数，如 "2"、"3"、"5" 等
    
    Returns:
        响应对象，包含设置结果
        失败时返回 None
    
    API 端点：
        POST /margin/leverage/user_market_setting
    
    注意事项：
        与 set_cex_unified_leverage 的区别：
        - set_cex_margin_leverage: 保证金账户（Margin）
        - set_cex_unified_leverage: 统一账户（Unified）
    """
    try:
        lever_setting = MarginMarketLeverage(
            currency_pair=currency,
            leverage=leverage
        )
        return margin_api.set_user_market_leverage(lever_setting)
    except Exception as e:
        logger.error(f"设置保证金杠杆失败 currency={currency}, leverage={leverage}, error={e}")
        return None


def set_cex_leverage(contract: str, leverage: str):
    """
    设置合约仓位杠杆倍数
    
    功能：
    - 为指定合约设置杠杆倍数
    - 影响该合约的开仓和持仓
    
    Args:
        contract (str): 合约名称，如 "BTC_USDT"
        leverage (str): 杠杆倍数，如 "2"、"5"、"10" 等
    
    Returns:
        响应对象，包含设置结果
        失败时返回 None
    
    注意事项：
        - 杠杆倍数越高，保证金要求越低，但爆仓风险越大
        - 建议使用 2-3 倍杠杆以控制风险
        - 必须在开仓前或无持仓时设置
    
    应用场景：
        资金费率套利中，设置合约杠杆
    """
    try:
        return futures_api.update_position_leverage(settle, contract, leverage)
    except Exception as e:
        logger.error(f"设置仓位杠杆失败 contract={contract}, leverage={leverage}, error={e}")
        return None


def set_cex_dual_mode(dual_mode=True):
    """
    设置合约持仓模式（单向/双向）
    
    功能：
    - 单向持仓模式：同一合约只能持有一个方向（多或空）
    - 双向持仓模式：同一合约可以同时持有多空双向仓位
    
    Args:
        dual_mode (bool, optional): 持仓模式，默认 True
            - True: 双向持仓模式
            - False: 单向持仓模式
    
    Returns:
        响应对象，包含设置结果
        失败时返回 None
    
    持仓模式对比：
        ┌─────────────┬──────────────┬──────────────┐
        │   模式      │   单向模式   │   双向模式   │
        ├─────────────┼──────────────┼──────────────┤
        │ 持仓方向    │ 只能多或空   │ 可同时多空   │
        │ 保证金占用  │ 较少         │ 较多         │
        │ 适用场景    │ 套利策略     │ 对冲策略     │
        └─────────────┴──────────────┴──────────────┘
    
    应用场景：
        资金费率套利使用单向持仓模式（False）
    """
    try:
        return futures_api.set_dual_mode(settle, dual_mode)
    except Exception as e:
        logger.error(f"设置双模式失败 dual_mode={dual_mode}, error={e}")
        return None


# ==================== 持仓查询相关 ====================

def get_cex_position(contract: str):
    """
    获取指定合约的持仓信息
    
    功能：
    - 查询单个合约的持仓详情
    - 包含持仓数量、方向、盈亏等信息
    
    Args:
        contract (str): 合约名称，如 "BTC_USDT"
    
    Returns:
        Position: 持仓对象，包含以下关键字段：
            - contract: 合约名称
            - size: 持仓数量（正数=多，负数=空）
            - leverage: 杠杆倍数
            - unrealised_pnl: 未实现盈亏（浮动盈亏）
            - realised_pnl: 已实现盈亏（包含资金费率）
            - entry_price: 开仓均价
            - mark_price: 标记价格
        失败时返回 None
    
    应用场景：
        检查是否已有持仓，避免重复开仓
    """
    try:
        return futures_api.get_position(settle, contract)
    except Exception as e:
        logger.error(f"获取仓位信息失败 contract={contract}, error={e}")
        return None


def get_cex_all_position():
    """
    获取所有合约的持仓信息
    
    功能：
    - 查询所有持仓中的合约
    - 只返回有持仓的合约（holding=True）
    
    Returns:
        list[Position]: 持仓列表，每个元素包含：
            - contract: 合约名称
            - size: 持仓数量
            - leverage: 杠杆倍数
            - unrealised_pnl: 未实现盈亏
            - realised_pnl: 已实现盈亏（含资金费率）
            - entry_price: 开仓均价
        失败时返回 None
    
    应用场景：
        - 监控所有持仓的盈亏情况
        - 检查是否有持仓（防止重复开仓）
        - 批量平仓操作
    """
    try:
        return futures_api.list_positions(settle, holding=True)
    except Exception as e:
        logger.error(f"获取所有仓位信息失败: {e}")
        return None


# ==================== 订单查询相关 ====================

def find_cex_spot_orders(currency: str):
    """
    查询现货历史订单（已完成）
    
    功能：
    - 查询指定交易对的已完成订单
    - 用于计算现货持仓成本和盈亏
    
    Args:
        currency (str): 交易对，如 "BTC_USDT"
    
    Returns:
        list[Order]: 订单列表，每个订单包含：
            - id: 订单ID
            - currency_pair: 交易对
            - side: 买卖方向（buy/sell）
            - amount: 交易数量
            - price: 委托价格
            - avg_deal_price: 平均成交价
            - fee: 手续费
            - status: 订单状态（finished）
            - create_time: 创建时间
            - update_time_ms: 更新时间（毫秒）
        失败时返回 None
    
    API 端点：
        GET /spot/orders
    
    应用场景：
        计算现货持仓盈亏，判断是否需要平仓
    """
    try:
        return spot_api.list_orders(currency_pair=currency, status="finished")
    except Exception as e:
        logger.error(f"查询现货订单失败 currency={currency}, error={e}")
        return None


def get_cex_spot_accounts(currency: str):
    """
    获取统一账户余额信息
    
    功能：
    - 查询指定币种在统一账户的余额
    - 包含可用余额、冻结余额、借贷余额等
    
    Args:
        currency (str): 币种名称，如 "BTC"、"USDT"
    
    Returns:
        list[UnifiedAccount]: 账户信息列表，包含：
            - currency: 币种
            - available: 可用余额
            - freeze: 冻结余额
            - borrowed: 已借余额
            - interest: 利息
        失败时返回 None
    
    应用场景：
        检查账户余额是否充足
    """
    try:
        return unified_api.list_unified_accounts(currency=currency)
    except Exception as e:
        logger.error(f"获取现货账户信息失败 currency={currency}, error={e}")
        return None


# ==================== 行情数据相关 ====================

def get_cex_futures_candle(contract: str, interval="5m", limit=100):
    """
    获取合约K线数据
    
    功能：
    - 获取指定合约的历史K线数据
    - 用于技术分析和策略回测
    
    Args:
        contract (str): 合约名称，如 "BTC_USDT"
        interval (str, optional): K线周期，默认 "5m"
            可选值：
            - "1m": 1分钟
            - "5m": 5分钟
            - "15m": 15分钟
            - "1h": 1小时
            - "4h": 4小时
            - "1d": 1天
        limit (int, optional): 返回数量，默认 100
            最大值：1000
    
    Returns:
        list[Candlestick]: K线数据列表，每根K线包含：
            - t: 时间戳
            - o: 开盘价
            - h: 最高价
            - l: 最低价
            - c: 收盘价
            - v: 成交量
        失败时返回 None
    
    应用场景：
        技术分析、策略回测、趋势判断
    """
    try:
        return futures_api.list_futures_candlesticks(settle, contract, interval=interval, limit=limit)
    except Exception as e:
        logger.error(f"获取合约K线失败 contract={contract}, interval={interval}, limit={limit}, error={e}")
        return None


def get_cex_spot_candle(contract: str, interval="5m", limit=100):
    """
    获取现货K线数据
    
    功能：
    - 获取指定交易对的历史K线数据
    - 用于现货市场分析
    
    Args:
        contract (str): 交易对，如 "BTC_USDT"
        interval (str, optional): K线周期，默认 "5m"
            可选值：
            - "1m": 1分钟
            - "5m": 5分钟
            - "15m": 15分钟
            - "1h": 1小时
            - "4h": 4小时
            - "1d": 1天
        limit (int, optional): 返回数量，默认 100
            最大值：1000
    
    Returns:
        list[Candlestick]: K线数据列表，每根K线包含：
            - t: 时间戳（秒）
            - o: 开盘价
            - h: 最高价
            - l: 最低价
            - c: 收盘价
            - v: 成交量
            - a: 交易额
        失败时返回 None
    
    应用场景：
        - 验证交易对是否可用（策略中用于检测）
        - 现货市场技术分析
    """
    try:
        return spot_api.list_candlesticks(contract, interval=interval, limit=limit)
    except Exception as e:
        logger.error(f"获取现货K线失败 contract={contract}, interval={interval}, limit={limit}, error={e}")
        return None


def get_cex_fticker(contract: str):
    """
    获取合约实时行情（Ticker）
    
    功能：
    - 获取指定合约的实时价格和盘口信息
    - 包含买卖价、24h涨跌幅、成交量等
    
    Args:
        contract (str): 合约名称，如 "BTC_USDT"
    
    Returns:
        list[FuturesTicker]: 行情列表（通常只有一个元素），包含：
            - contract: 合约名称
            - last: 最新成交价
            - lowest_ask: 卖一价（做多时参考）
            - highest_bid: 买一价（做空时参考）
            - change_percentage: 24h涨跌幅
            - high_24h: 24h最高价
            - low_24h: 24h最低价
            - volume_24h: 24h成交量
            - funding_rate: 当前资金费率
            - mark_price: 标记价格
            - index_price: 指数价格
        失败时返回 None
    
    应用场景：
        - 获取合约买卖价，用于计算开仓数量
        - 监控资金费率变化
        - 获取市场深度信息
    """
    try:
        return futures_api.list_futures_tickers(settle, contract=contract)
    except Exception as e:
        logger.error(f"获取合约行情失败 contract={contract}, error={e}")
        return None


def get_cex_sticker(contract: str):
    """
    获取现货实时行情（Ticker）
    
    功能：
    - 获取指定交易对的实时价格和盘口信息
    - 用于现货下单和价格监控
    
    Args:
        contract (str): 交易对，如 "BTC_USDT"
    
    Returns:
        list[Ticker]: 行情列表（通常只有一个元素），包含：
            - currency_pair: 交易对
            - last: 最新成交价
            - lowest_ask: 卖一价（买入时参考）
            - highest_bid: 买一价（卖出时参考）
            - change_percentage: 24h涨跌幅
            - high_24h: 24h最高价
            - low_24h: 24h最低价
            - base_volume: 24h成交量（基础币）
            - quote_volume: 24h成交额（计价币）
        失败时返回 None
    
    应用场景：
        - 获取现货买卖价，用于计算开仓成本
        - 计算现货持仓盈亏
        - 监控市场流动性
    """
    try:
        return spot_api.list_tickers(currency_pair=contract)
    except GateApiException as e:
        logger.error(f"获取现货行情失败 contract={contract}, error={e}")
        return None


# ==================== 测试代码（请勿在生产环境执行） ====================
# 以下代码仅用于开发测试，生产环境请注释掉

# 测试平仓
# cex_futures_close_position("SOL_USDT")

# 测试合约做空 + 现货做多
# cex_futures_place("SOL_USDT", "0", -1)  # 合约做空1张
# cex_spot_place("SOL_USDT", "buy", "160")  # 现货买入160 USDT

# 测试现货做空
# cex_spot_place("SOL_USDT", "sell", "1")  # 卖出1个SOL

