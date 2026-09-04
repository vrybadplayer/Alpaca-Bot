#!/usr/bin/env python3
"""
Utility classes and shared components for the Worker-Critic system.
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables from .env in the Alpaca-Bot root
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# ==================== ENUMS AND BASE CLASSES ====================

class OrderAction:
    BUY = "buy"
    SELL = "sell"

class OrderType:
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus:
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class OrderContract:
    def __init__(self, ticker: str, action: OrderAction, quantity: int,
                 order_type: OrderType = OrderType.MARKET,
                 price: float = None, stop_price: float = None,
                 source_component: str = "unknown"):
        self.ticker = ticker
        self.action = action
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.source_component = source_component
        self.order_id = None
        self.execution_price = None
        self.executed_quantity = 0
        self.status = OrderStatus.PENDING
        self.fees = 0.0
        self.slippage = 0.0
        # Use timezone-aware UTC datetime
        self.execution_timestamp = None
        self.notes = ""

class TradeSignal:
    def __init__(self, ticker: str, action: OrderAction, quantity: int,
                 target_price: float, stop_loss: float, take_profit: float,
                 confidence: float, timestamp: datetime,
                 source: str, rationale: str):
        self.ticker = ticker
        self.action = action
        self.quantity = quantity
        self.target_price = target_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.confidence = confidence
        self.timestamp = timestamp
        self.source = source
        self.rationale = rationale

class PortfolioState:
    def __init__(self, cash_balance: float, total_equity: float,
                 realized_pnl: float, unrealized_pnl: float,
                 positions: List[Dict[str, Any]] = None):
        self.cash_balance = cash_balance
        self.total_equity = total_equity
        self.realized_pnl = realized_pnl
        self.unrealized_pnl = unrealized_pnl
        self.positions = positions or []
        self.reserve_limit = 5000.0  # Default cash reserve

# ==================== VECTOR STORE (STUB) ====================
class VectorStore:
    def __init__(self, persist_directory: str = None, collection_name: str = None):
        self.persist_directory = persist_directory
        self.collection_name = collection_name

    def is_available(self) -> bool:
        return False

    def add_text(self, text: str, metadata: Dict[str, Any] = None) -> bool:
        return False

    def add_post_mortem_autopsy(self, autopsy_data: Dict[str, Any]) -> bool:
        return False

    def query_loss_reflections(self, query_text: str, n_results: int = 3, ticker: str = None) -> List[Dict[str, Any]]:
        return []

    def add_trade_memory(self, trade_data: Dict[str, Any]) -> bool:
        return False

    def query_knowledge(self, query_text: str, n_results: int = 5, filter_dict: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return []

    def query_market_psychology(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        return []

    def query_regime_indicators(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        return []

    def get_collection_count(self) -> int:
        return 0

    def reset_collection(self) -> bool:
        return False

# ==================== OLLAMA CLIENT ====================
# Import the real Ollama client
from Core.Setups.ollama_client import OllamaClient

# ==================== PORTFOLIO MANAGER (STUB) ====================
class PortfolioManager:
    def __init__(self, initial_cash: float = 100000.0, reserve_limit: float = 5000.0):
        self.cash_balance = initial_cash
        self.total_equity = initial_cash
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.positions = []
        self.reserve_limit = reserve_limit

    def get_state(self) -> PortfolioState:
        return PortfolioState(
            cash_balance=self.cash_balance,
            total_equity=self.total_equity,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            positions=self.positions
        )

    def get_position_quantity(self, ticker: str) -> int:
        for pos in self.positions:
            if pos.get("ticker") == ticker:
                return pos.get("quantity", 0)
        return 0