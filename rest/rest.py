from gate_api import Configuration, FuturesApi, ApiClient, FuturesOrder, MarginApi, SpotApi, Order, UnifiedApi, \
    UnifiedLeverageSetting

host = 'https://api.gateio.ws'

config = Configuration(
    key='',
    secret='',
    host="https://api.gateio.ws/api/v4"
)

margin_api = MarginApi(ApiClient(config))

spot_api = SpotApi(ApiClient(config))

unified_api = UnifiedApi(ApiClient(config))

futures_api = FuturesApi(ApiClient(config))

settle="usdt"
def get_cex_contracts():
    try:
        return futures_api.list_futures_contracts("usdt")
    except:
        pass


def cex_futures_place(contract:str, price:str, size:int):

    tif = 'gtc'
    if price == '0' or price == '' :
        tif = 'ioc'
    else:
        tif = 'gtc'

    order = FuturesOrder(contract=contract, size=size, price=price, tif=tif,iceberg=0)
    return futures_api.create_futures_order(settle, order)

def cex_spot_place(currency_pair:str, side:str,price:str, amount:str,tp="market"):
    """
    现货下单
    """
    tif = 'gtc'
    if price == '0' or price == '' :
        tif = 'ioc'
    else:
        tif = 'gtc'

    order = Order(
        currency_pair=currency_pair,
        amount=amount,
        side=side,
        price=price,
        time_in_force=tif,
        type=tp,
        account="margin",
        auto_borrow=True,
        auto_repay=True,
        iceberg="0"
    )
    return spot_api.create_order(order)

def get_cex_close(contract:str,auto_size:str, price="0"):

    # close boolean 设置为 true 的时候执行平仓操作，并且size应设置为0
    tif = 'gtc'
    if price == "0" :
        tif = 'ioc'
        price = 0
    else:
        tif = 'gtc'

    order = FuturesOrder(contract=contract, size=0, price=price,auto_size=auto_size,reduce_only=True,close=True, tif=tif)
    return futures_api.create_futures_order(settle, order)

def get_cex_unified_leverage(contract:str):
   """
   获取用户最大、最小可设置币种杠杆倍数
   """
   return unified_api.get_user_leverage_currency_config_with_http_info(contract)

def set_cex_unified_leverage(currency:str,leverage: str):
   """
   获取用户最大、最小可设置币种杠杆倍数
   """
   lever_setting = UnifiedLeverageSetting(
       currency=currency,
       leverage=leverage
   )
   return unified_api.set_user_leverage_currency_setting_with_http_info(lever_setting)

def set_cex_leverage(contract:str, leverage:str):
   return futures_api.update_position_leverage(settle, contract,leverage)


def set_cex_dual_mode(dual_mode=True):
    return futures_api.set_dual_mode(settle, dual_mode)


def get_cex_position(contract:str):
    return futures_api.get_position(settle,contract)

def get_cex_all_position():
    return futures_api.list_positions_with_http_info(settle)

def get_cex_futures_candle(contract:str, interval="5m", limit=100):
    try:
        return futures_api.list_futures_candlesticks(settle,contract,interval=interval,limit=limit)
    except:
        pass

def get_cex_spot_candle(contract:str, interval="5m", limit=100):
    try:
        return spot_api.list_candlesticks(contract,interval=interval,limit=limit)
    except:
        pass


