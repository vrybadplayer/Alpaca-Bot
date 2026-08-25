import Core.Setups.config as config
from alpaca.trading.client import TradingClient

trading_client = TradingClient(config.API, config.SECRET)

positions = trading_client.get_all_positions()

for position in positions:
    print(position.symbol, position.current_price)