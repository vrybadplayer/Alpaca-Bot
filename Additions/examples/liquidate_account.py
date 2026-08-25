import Core.Setups.config as config
from alpaca.trading.client import TradingClient

trading_client = TradingClient(config.API, config.SECRET)

trading_client.close_all_positions(True)