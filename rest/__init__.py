"""REST API 模块：包含 CCXT 统一接口封装和可选的 Gate.io API 客户端"""

# 可选导入 api_client（如果安装了 gate_api）
try:
    from .api_client import (
        GateApiClient,
        get_api_clients,
        init_api_client_from_env,
        get_default_client
    )
    _HAS_API_CLIENT = True
except ImportError:
    # 如果没有安装 gate_api，api_client 不可用
    _HAS_API_CLIENT = False
    GateApiClient = None
    get_api_clients = None
    init_api_client_from_env = None
    get_default_client = None

# 从 CCXT 客户端导入所有函数（替代原来的 rest.py）
from .ccxt_client import (
    # 客户端
    CCXTClient,
    get_ccxt_client,
    init_ccxt_client,
    
    # 数据类
    Contract,
    Ticker,
    Position,
    OrderInfo,
    WalletBalance,
    
    # 合约API
    get_cex_contracts,
    get_cex_fticker,
    cex_futures_place,
    cex_futures_close_position,
    get_cex_position,
    get_cex_all_position,
    set_cex_leverage,
    set_cex_dual_mode,
    
    # 现货API
    get_cex_sticker,
    get_cex_spot_candle,
    cex_spot_place,
    cex_spot_close_position,
    find_cex_spot_orders,
    set_cex_margin_leverage,
    set_cex_unified_leverage,
    
    # 账户API
    get_cex_wallet_balance,
)

__all__ = [
    # CCXT 客户端（主要使用）
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
    'cex_spot_close_position',
    'find_cex_spot_orders',
    'set_cex_margin_leverage',
    'set_cex_unified_leverage',
    
    # 账户API
    'get_cex_wallet_balance',
]

# 如果 api_client 可用，也导出相关函数
if _HAS_API_CLIENT:
    __all__.extend([
        'GateApiClient',
        'get_api_clients',
        'init_api_client_from_env',
        'get_default_client',
    ])

