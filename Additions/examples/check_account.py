import Core.Setups.config as config
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

trading_client = TradingClient(config.API, config.SECRET)

print(trading_client.get_account().account_number)
print(trading_client.get_account().buying_power)
