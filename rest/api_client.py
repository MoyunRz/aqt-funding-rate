"""
Gate.io API 客户端管理模块

============================================================
模块功能
============================================================
本模块负责管理 Gate.io API 的配置和客户端初始化，包括：

1. API 配置管理
   - 从配置文件或环境变量加载 API 密钥
   - 支持正式环境和测试网切换
   - 提供默认配置和自定义配置

2. API 客户端管理
   - 统一管理所有 API 客户端实例
   - 单例模式，避免重复创建
   - 提供便捷的客户端获取方法

3. 安全性
   - 避免 API 密钥硬编码
   - 支持从环境变量读取
   - 配置文件独立管理

============================================================
使用方法
============================================================
方式一：使用默认配置
    from rest.api_client import get_api_clients
    
    clients = get_api_clients()
    futures_api = clients['futures_api']

方式二：使用自定义配置
    from rest.api_client import GateApiClient
    
    client = GateApiClient(
        api_key='your_key',
        api_secret='your_secret',
        use_testnet=False
    )
    futures_api = client.get_futures_api()

方式三：从环境变量加载
    export GATE_API_KEY="your_key"
    export GATE_API_SECRET="your_secret"
    export GATE_USE_TESTNET="false"
    
    from rest.api_client import get_api_clients
    clients = get_api_clients()

============================================================
"""

import os
import logging
from typing import Optional, Dict
from gate_api import (
    Configuration, 
    ApiClient, 
    FuturesApi, 
    MarginApi, 
    SpotApi, 
    UnifiedApi, 
    WalletApi
)

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


class GateApiClient:
    """
    Gate.io API 客户端管理器
    
    功能：
    - 管理 API 配置和认证
    - 创建和管理各类 API 客户端
    - 支持单例模式
    
    属性：
        config: Gate.io API 配置对象
        margin_api: 保证金/杠杆交易 API
        spot_api: 现货交易 API
        unified_api: 统一账户 API
        futures_api: 合约交易 API
        wallet_api: 钱包 API
    """
    
    # 类变量：单例实例
    _instance: Optional['GateApiClient'] = None
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        use_testnet: bool = True,
        settle: str = "usdt"
    ):
        """
        初始化 Gate.io API 客户端
        
        Args:
            api_key (str, optional): API Key
                - 如果不提供，则从环境变量 GATE_API_KEY 读取
                - 再不提供，则使用默认测试密钥（仅测试网）
            api_secret (str, optional): API Secret
                - 如果不提供，则从环境变量 GATE_API_SECRET 读取
                - 再不提供，则使用默认测试密钥（仅测试网）
            use_testnet (bool, optional): 是否使用测试网，默认 True
                - True: 使用测试网（https://api-testnet.gateapi.io/api/v4）
                - False: 使用正式环境（https://api.gateio.ws/api/v4）
            settle (str, optional): 结算货币，默认 "usdt"
                - "usdt": USDT 结算
                - "btc": BTC 结算
        """
        self.settle = settle
        self.use_testnet = use_testnet
        
        # ==================== 第1步：获取 API 密钥 ====================
        # 优先级：参数 > 环境变量 > 默认值
        self.api_key = api_key or os.getenv('GATE_API_KEY') or self._get_default_key()
        self.api_secret = api_secret or os.getenv('GATE_API_SECRET') or self._get_default_secret()
        
        # ==================== 第2步：确定 API 主机地址 ====================
        if use_testnet:
            # 测试网地址
            self.host = "https://api-testnet.gateapi.io/api/v4"
            logger.info("使用 Gate.io 测试网环境")
        else:
            # 正式环境地址
            self.host = "https://api.gateio.ws/api/v4"
            logger.info("使用 Gate.io 正式环境")
        
        # ==================== 第3步：创建 API 配置 ====================
        self.config = Configuration(
            key=self.api_key,
            secret=self.api_secret,
            host=self.host
        )
        
        # ==================== 第4步：初始化 API 客户端 ====================
        self._api_client = ApiClient(self.config)
        
        # 创建各类 API 实例
        self.margin_api = MarginApi(self._api_client)      # 保证金/杠杆交易
        self.spot_api = SpotApi(self._api_client)          # 现货交易
        self.unified_api = UnifiedApi(self._api_client)    # 统一账户
        self.futures_api = FuturesApi(self._api_client)    # 合约交易
        self.wallet_api = WalletApi(self._api_client)      # 钱包
        
        logger.info(f"Gate.io API 客户端初始化成功，结算货币: {settle}")
    
    def _get_default_key(self) -> str:
        """
        获取默认 API Key（仅测试网）
        
        Returns:
            str: 默认 API Key
        
        警告：
            生产环境请务必使用自己的 API 密钥！
        """
        if self.use_testnet:
            return '18c9b6413645f921935f00b0cd405e6e'
        else:
            raise ValueError(
                "生产环境必须提供 API Key！\n"
                "请通过以下方式之一提供：\n"
                "1. 传入 api_key 参数\n"
                "2. 设置环境变量 GATE_API_KEY\n"
                "3. 在配置文件中设置"
            )
    
    def _get_default_secret(self) -> str:
        """
        获取默认 API Secret（仅测试网）
        
        Returns:
            str: 默认 API Secret
        
        警告：
            生产环境请务必使用自己的 API 密钥！
        """
        if self.use_testnet:
            return 'e7d12abf7a8f9240224c57f09ad3f48d1baec366b219054a60331282a8edafc4'
        else:
            raise ValueError(
                "生产环境必须提供 API Secret！\n"
                "请通过以下方式之一提供：\n"
                "1. 传入 api_secret 参数\n"
                "2. 设置环境变量 GATE_API_SECRET\n"
                "3. 在配置文件中设置"
            )
    
    @classmethod
    def get_instance(
        cls,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        use_testnet: bool = True,
        settle: str = "usdt",
        force_new: bool = False
    ) -> 'GateApiClient':
        """
        获取 API 客户端单例实例
        
        Args:
            api_key (str, optional): API Key
            api_secret (str, optional): API Secret
            use_testnet (bool, optional): 是否使用测试网，默认 True
            settle (str, optional): 结算货币，默认 "usdt"
            force_new (bool, optional): 是否强制创建新实例，默认 False
        
        Returns:
            GateApiClient: API 客户端实例
        
        说明：
            - 使用单例模式，多次调用返回同一实例
            - 如果需要创建新实例，设置 force_new=True
        """
        if cls._instance is None or force_new:
            cls._instance = cls(
                api_key=api_key,
                api_secret=api_secret,
                use_testnet=use_testnet,
                settle=settle
            )
        return cls._instance
    
    def get_margin_api(self) -> MarginApi:
        """获取保证金/杠杆交易 API"""
        return self.margin_api
    
    def get_spot_api(self) -> SpotApi:
        """获取现货交易 API"""
        return self.spot_api
    
    def get_unified_api(self) -> UnifiedApi:
        """获取统一账户 API"""
        return self.unified_api
    
    def get_futures_api(self) -> FuturesApi:
        """获取合约交易 API"""
        return self.futures_api
    
    def get_wallet_api(self) -> WalletApi:
        """获取钱包 API"""
        return self.wallet_api
    
    def get_settle(self) -> str:
        """获取结算货币"""
        return self.settle
    
    def get_all_apis(self) -> Dict[str, any]:
        """
        获取所有 API 客户端
        
        Returns:
            dict: 包含所有 API 客户端的字典
                {
                    'margin_api': MarginApi,
                    'spot_api': SpotApi,
                    'unified_api': UnifiedApi,
                    'futures_api': FuturesApi,
                    'wallet_api': WalletApi,
                    'settle': str
                }
        """
        return {
            'margin_api': self.margin_api,
            'spot_api': self.spot_api,
            'unified_api': self.unified_api,
            'futures_api': self.futures_api,
            'wallet_api': self.wallet_api,
            'settle': self.settle
        }


# ==================== 便捷函数 ====================

def get_api_clients(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    use_testnet: bool = True,
    settle: str = "usdt"
) -> Dict[str, any]:
    """
    获取 Gate.io API 客户端（单例模式）
    
    这是最常用的函数，推荐使用！
    
    Args:
        api_key (str, optional): API Key
        api_secret (str, optional): API Secret
        use_testnet (bool, optional): 是否使用测试网，默认 True
        settle (str, optional): 结算货币，默认 "usdt"
    
    Returns:
        dict: 包含所有 API 客户端的字典
    
    使用示例：
        ```python
        from rest.api_client import get_api_clients
        
        # 获取所有 API 客户端
        clients = get_api_clients()
        
        # 使用合约 API
        futures_api = clients['futures_api']
        contracts = futures_api.list_futures_contracts(clients['settle'])
        
        # 使用现货 API
        spot_api = clients['spot_api']
        tickers = spot_api.list_tickers()
        ```
    """
    client = GateApiClient.get_instance(
        api_key=api_key,
        api_secret=api_secret,
        use_testnet=use_testnet,
        settle=settle
    )
    return client.get_all_apis()


def init_api_client_from_env() -> Dict[str, any]:
    """
    从环境变量初始化 API 客户端
    
    需要设置以下环境变量：
        - GATE_API_KEY: API Key
        - GATE_API_SECRET: API Secret
        - GATE_USE_TESTNET (可选): true/false，默认 true
        - GATE_SETTLE (可选): usdt/btc，默认 usdt
    
    Returns:
        dict: 包含所有 API 客户端的字典
    
    使用示例：
        ```bash
        # 设置环境变量
        export GATE_API_KEY="your_api_key"
        export GATE_API_SECRET="your_api_secret"
        export GATE_USE_TESTNET="false"
        export GATE_SETTLE="usdt"
        ```
        
        ```python
        from rest.api_client import init_api_client_from_env
        
        clients = init_api_client_from_env()
        futures_api = clients['futures_api']
        ```
    """
    use_testnet = os.getenv('GATE_USE_TESTNET', 'true').lower() == 'true'
    settle = os.getenv('GATE_SETTLE', 'usdt')
    
    return get_api_clients(
        use_testnet=use_testnet,
        settle=settle
    )


# ==================== 默认客户端实例 ====================
# 创建默认客户端实例，供直接导入使用
_default_client = None

def get_default_client() -> GateApiClient:
    """
    获取默认客户端实例
    
    Returns:
        GateApiClient: 默认客户端实例
    """
    global _default_client
    if _default_client is None:
        _default_client = GateApiClient.get_instance()
    return _default_client


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 示例1：使用默认配置（测试网）
    print("=" * 60)
    print("示例1：使用默认配置（测试网）")
    print("=" * 60)
    clients = get_api_clients()
    print(f"Settle: {clients['settle']}")
    print(f"Futures API: {clients['futures_api']}")
    
    # 示例2：使用自定义配置
    print("\n" + "=" * 60)
    print("示例2：使用自定义配置")
    print("=" * 60)
    custom_client = GateApiClient(
        api_key='your_key',
        api_secret='your_secret',
        use_testnet=True,
        settle='usdt'
    )
    print(f"Custom client created: {custom_client}")
    
    # 示例3：从环境变量加载（如果已设置）
    print("\n" + "=" * 60)
    print("示例3：从环境变量加载")
    print("=" * 60)
    try:
        env_clients = init_api_client_from_env()
        print(f"Environment client loaded: {env_clients['settle']}")
    except Exception as e:
        print(f"未设置环境变量: {e}")

