"""
REST API 模块

包含：
- api_client: API 客户端管理器
- rest: REST API 封装函数
"""

from .api_client import (
    GateApiClient,
    get_api_clients,
    init_api_client_from_env,
    get_default_client
)

from .rest import *

__all__ = [
    'GateApiClient',
    'get_api_clients',
    'init_api_client_from_env',
    'get_default_client'
]

