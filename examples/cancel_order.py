import config
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus

trading_client = TradingClient(config.API, config.SECRET)

request_params = GetOrdersRequest(
    status=QueryOrderStatus.OPEN
)

orders = trading_client.get_orders(request_params)

for order in orders:
    trading_client.cancel_order_by_id(order.id)
    print(order.id + "order cancelled")