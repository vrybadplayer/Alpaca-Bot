import config
from alpaca.data.live import StockDataStream

stream = StockDataStream(config.API, config.SECRET)

async def handle_trade(data):
    print(data)

stream.subscribe_trades(handle_trade, "NVDA")

stream.run()
