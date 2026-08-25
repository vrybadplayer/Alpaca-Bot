import Core.Setups.config as config
from alpaca.data import StockHistoricalDataClient, StockTradesRequest
from datetime import datetime

data_client = StockHistoricalDataClient(config.API, config.SECRET)

request_params = StockTradesRequest(
    symbol_or_symbols="NVDA",
    start=datetime(2026, 1, 30, 14, 30),
    end=datetime(2026, 1, 30, 14, 45)
)

trades = data_client.get_stock_trades(request_params)

for trade in trades.data["NVDA"]:
    print(trade)
    break