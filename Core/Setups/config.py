import os
from dotenv import load_dotenv

load_dotenv()

API = os.getenv("ALPACA_API_KEY")
SECRET = os.getenv("ALPACA_SECRET_KEY")

if not API:
    raise ValueError("Critical Error: API_KEY is missing from .env!")

if not SECRET:
    raise ValueError("Critical Error: ALPACA_SECRET_KEY is missing from .env!")
