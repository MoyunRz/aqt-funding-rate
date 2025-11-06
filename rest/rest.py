import logging
from gate_api.exceptions import GateApiException

# 配置日志记录
logger = logging.getLogger(__name__)

from gate_api import Configuration, FuturesApi, ApiClient, FuturesOrder, MarginApi, SpotApi, Order, UnifiedApi, \
    UnifiedLeverageSetting, WalletApi, MarginMarketLeverage

# host = 'https://api.gateio.ws'
host = "https://api-testnet.gateapi.io/api/v4"

config = Configuration(
    key='18c9b6413645f921935f00b0cd405e6e',
    secret='e7d12abf7a8f9240224c57f09ad3f48d1baec366b219054a60331282a8edafc4',
    host=host
)


margin_api = MarginApi(ApiClient(config))
spot_api = SpotApi(ApiClient(config))
unified_api = UnifiedApi(ApiClient(config))
futures_api = FuturesApi(ApiClient(config))
wallet_api = WalletApi(ApiClient(config))

settle="usdt"

def get_cex_contracts():
    try:
        return futures_api.list_futures_contracts("usdt")
    except Exception as e:
        logger.error(f"获取合约列表失败: {e}")
        return None

def get_cex_wallet_balance():
    try:
        return wallet_api.get_total_balance()
    except Exception as e:
        logger.error(f"获取钱包余额失败: {e}")
        return None

def cex_futures_close_position(contract: str):
    try:
        order = FuturesOrder(contract=contract, size=0, price="0", close=True,tif='ioc')
        return futures_api.create_futures_order(settle, order)
    except Exception as e:
        logger.error(f"合约平仓失败 contract={contract}, error={e}")
        return None

def cex_futures_place(contract: str, price: str, size: int):
    try:
        tif = 'gtc'
        if price == '0' or price == '':
            tif = 'ioc'
        else:
            tif = 'gtc'

        order = FuturesOrder(contract=contract, size=size, price=price, tif=tif, iceberg=0)
        return futures_api.create_futures_order(settle, order)
    except Exception as e:
        logger.error(f"合约下单失败 contract={contract}, price={price}, size={size}, error={e}")
        return None

def cex_spot_place(currency_pair: str, side: str,  amount: str,price="0"):
    """
    现货下单
    根据 Gate.io API v4 文档: https://www.gate.com/docs/developers/apiv4/zh_CN/#%E4%B8%8B%E5%8D%95
    :param currency_pair: 交易对，如 BTC_USDT
    :param side: 买卖方向 buy/sell
    :param price: 价格，市价单传 "0" 或 "" 或不传
    :param amount: 数量
    """
    try:
        # 判断是市价单还是限价单
        is_market_order = (price == '0' or price == '' or price == 0)
        
        if is_market_order:
            # 市价单配置
            # 根据 Gate.io API 文档，市价单不需要 price 和 time_in_force 参数
            # margin 账户的市价单不支持 auto_borrow 和 auto_repay 参数
            order = Order(
                currency_pair=currency_pair,
                type="market",
                time_in_force='ioc',
                side=side,
                amount=amount,
                account="unified",
                auto_borrow=True,
                auto_repay=True
            )
        else:
            # 限价单配置
            # 根据 Gate.io API 文档，限价单需要 price 参数
            # margin 账户支持 auto_borrow 和 auto_repay
            order = Order(
                currency_pair=currency_pair,
                type="limit",
                side=side,
                amount=amount,
                price=str(price),
                time_in_force='gtc',
                account="unified",
                auto_borrow=True,
                auto_repay=True
            )
        
        return spot_api.create_order(order)
    except GateApiException as e:
        logger.error(f"现货下单失败 currency_pair={currency_pair}, side={side}, price={price}, amount={amount}, error={e}")
        logger.error(f"详细错误: {e.label}: {e.message}")
        if hasattr(e, 'body') and e.body:
            logger.error(f"响应体: {e.body}")
        return None
    except Exception as e:
        logger.error(f"现货下单异常 currency_pair={currency_pair}, side={side}, price={price}, amount={amount}, error={e}")
        return None

def cex_close_position(contract: str, auto_size: str, price="0"):
    try:
        # close boolean 设置为 true 的时候执行平仓操作，并且size应设置为0
        tif = 'gtc'
        if price == "0":
            tif = 'ioc'
            price = 0
        else:
            tif = 'gtc'

        order = FuturesOrder(contract=contract, size=0, price=price, auto_size=auto_size, reduce_only=True, close=False,tif=tif)
        return futures_api.create_futures_order(settle, order)
    except Exception as e:
        logger.error(f"获取平仓订单失败 contract={contract}, auto_size={auto_size}, price={price}, error={e}")
        return None

def get_cex_unified_leverage(contract: str):
    """
    获取用户最大、最小可设置币种杠杆倍数
    """
    try:
        return unified_api.get_user_leverage_currency_config_with_http_info(contract)
    except Exception as e:
        logger.error(f"获取统一杠杆配置失败 contract={contract}, error={e}")
        return None

def set_cex_unified_leverage(currency: str, leverage: str):
    """
    获取用户最大、最小可设置币种杠杆倍数
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
    /margin/leverage/user_market_setting
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

def find_cex_spot_orders(currency: str):
    """
    /spot/orders
    """
    try:
        return spot_api.list_orders(currency_pair=currency, status="finished")
    except Exception as e:
        logger.error(f"查询现货订单失败 currency={currency}, error={e}")
        return None

def set_cex_leverage(contract: str, leverage: str):
    try:
        return futures_api.update_position_leverage(settle, contract, leverage)
    except Exception as e:
        logger.error(f"设置仓位杠杆失败 contract={contract}, leverage={leverage}, error={e}")
        return None

def set_cex_dual_mode(dual_mode=True):
    try:
        return futures_api.set_dual_mode(settle, dual_mode)
    except Exception as e:
        logger.error(f"设置双模式失败 dual_mode={dual_mode}, error={e}")
        return None

def get_cex_position(contract: str):
    try:
        return futures_api.get_position(settle, contract)
    except Exception as e:
        logger.error(f"获取仓位信息失败 contract={contract}, error={e}")
        return None

def get_cex_all_position():
    try:
        return futures_api.list_positions(settle, holding=True)
    except Exception as e:
        logger.error(f"获取所有仓位信息失败: {e}")
        return None

def get_cex_spot_accounts(currency: str):
    try:
        return unified_api.list_unified_accounts(currency=currency)
    except Exception as e:
        logger.error(f"获取现货账户信息失败 currency={currency}, error={e}")
        return None

def get_cex_futures_candle(contract: str, interval="5m", limit=100):
    try:
        return futures_api.list_futures_candlesticks(settle, contract, interval=interval, limit=limit)
    except Exception as e:
        logger.error(f"获取合约K线失败 contract={contract}, interval={interval}, limit={limit}, error={e}")
        return None

def get_cex_spot_candle(contract: str, interval="5m", limit=100):
    try:
        return spot_api.list_candlesticks(contract, interval=interval, limit=limit)
    except Exception as e:
        logger.error(f"获取现货K线失败 contract={contract}, interval={interval}, limit={limit}, error={e}")
        return None

def get_cex_fticker(contract: str):
    try:
        return futures_api.list_futures_tickers(settle, contract=contract)
    except Exception as e:
        logger.error(f"获取合约行情失败 contract={contract}, error={e}")
        return None

def get_cex_sticker(contract: str):
    try:
        return spot_api.list_tickers(currency_pair=contract)
    except GateApiException as e:
        logger.error(f"获取现货行情失败 contract={contract}, error={e}")
        return None

cex_futures_close_position("SOL_USDT")

# 合约做空
# cex_futures_place("SOL_USDT", "0", 1)
# cex_spot_place("SOL_USDT", "buy",  "160")
#
#
# cex_spot_place("SOL_USDT", "sell",  "1")

