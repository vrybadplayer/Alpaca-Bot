import config
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce 

trading_client = TradingClient(config.API, config.SECRET)

# Market Buy, not LIMIT Buy
market_order_data = MarketOrderRequest(
    symbol="NVDA",
    qty=1,
    side=OrderSide.BUY, #SELL
    time_in_force=TimeInForce.DAY
)

market_order = trading_client.submit_order(market_order_data)
print(market_order)

# LIMIT Buy
limit_order_data = LimitOrderRequest(
    symbol="NVDA",
    qty=1,
    side=OrderSide.BUY, # SELL
    time_in_force=TimeInForce.DAY,
    limit_price=215.30
)


limit_order = trading_client.submit_order(limit_order_data)
print(limit_order)