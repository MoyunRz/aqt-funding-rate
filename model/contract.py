# model/contract.py
from dataclasses import dataclass, fields
from typing import Union, Optional, List
import json

from ccxt.static_dependencies.marshmallow.fields import Boolean


@dataclass
class Contract:
    """
    期货合约信息数据结构体
    """
    name: str
    type: str
    quanto_multiplier: str
    ref_discount_rate: str
    order_price_deviate: str
    maintenance_rate: str
    mark_type: str
    last_price: str
    mark_price: str
    index_price: str
    funding_rate_indicative: str
    mark_price_round: str
    funding_offset: int
    in_delisting: bool
    risk_limit_base: str
    interest_rate: str
    order_price_round: str
    order_size_min: int
    ref_rebate_rate: str
    funding_interval: int
    risk_limit_step: str
    leverage_min: str
    leverage_max: str
    risk_limit_max: str
    maker_fee_rate: str
    taker_fee_rate: str
    funding_rate: str
    order_size_max: int
    funding_next_apply: int
    short_users: int
    config_change_time: int
    trade_size: int
    position_size: int
    long_users: int
    funding_impact_value: str
    orders_limit: int
    trade_id: int
    orderbook_id: int
    enable_bonus: bool
    enable_credit: bool
    create_time: int
    funding_cap_ratio: str
    status: str
    launch_time: int
    cross_leverage_default: Optional[str] = None
    funding_rate_limit: Optional[str] = None
    voucher_leverage: Optional[str] = None
    is_pre_market: Optional[Boolean] = None
    enable_circuit_breaker: Optional[Boolean] = None
    delisting_time: Optional[int] = None
    delisted_time: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Contract':
        """
        从字典创建Contract实例

        Args:
            data: 包含合约信息的字典

        Returns:
            Contract: 合约对象实例
        """
        # 获取所有字段名
        field_names = {field.name for field in fields(cls)}
        
        # 只保留Contract类中定义的字段
        filtered_data = {key: value for key, value in data.items() if key in field_names}
        
        return cls(**filtered_data)
        
    @classmethod
    def from_json(cls, json_str: str) -> 'Contract':
        """
        从JSON字符串创建Contract实例

        Args:
            json_str: 包含合约信息的JSON字符串

        Returns:
            Contract: 合约对象实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
        
    @classmethod
    def from_json_array(cls, json_data: Union[str, List[dict]]) -> List['Contract']:
        """
        从JSON数组字符串或字典列表创建Contract实例数组

        Args:
            json_data: 包含合约信息数组的JSON字符串或字典列表

        Returns:
            List[Contract]: 合约对象实例数组
        """
        # 如果输入是字符串，则解析为对象
        if isinstance(json_data, str):
            data_list = json.loads(json_data)
        else:
            # 如果输入已经是一个列表，则直接使用
            data_list = json_data
            
        return [cls.from_dict(data) for data in data_list]