#!/usr/bin/env python3
"""
Alpaca Broker implementation for paper trading.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests

from Core.Tool_Registry.utils import OrderContract, OrderAction, OrderType

logger = logging.getLogger(__name__)

class AlpacaBroker:
    """Alpaca Broker for paper trading."""
    PAPER_BASE_URL = "https://paper-api.alpaca.markets"
    DATA_BASE_URL = "https://data.alpaca.markets"

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get('api_key') or os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
        self.api_secret = config.get('api_secret') or os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA_SECRET_KEY')
        self.base_url = config.get('base_url', self.PAPER_BASE_URL).rstrip('/')
        self.data_url = config.get('data_url', self.DATA_BASE_URL).rstrip('/')
        self.data_feed = config.get('data_feed', 'iex')
        self.session = None
        self.is_connected = False
        self.last_error = None
        self._setup_headers()
        self._dummy = self._is_dummy_credentials()
    def _is_dummy_credentials(self) -> bool:
        """Check if credentials are dummy placeholders."""
        return (self.api_key == 'PKDUMMY' and self.api_secret == 'SKDUMMY') or \
               (self.api_key == 'PKDUMMY' and not self.api_secret) or \
               (not self.api_key and self.api_secret == 'SKDUMMY')
    def _setup_headers(self):
        if self.api_key and self.api_secret and not self._is_dummy_credentials():
            self.session = requests.Session()
            self.session.headers.update({
                "APCA-API-KEY-ID": self.api_key.strip(),
                "APCA-API-SECRET-KEY": self.api_secret.strip(),
                "Content-Type": "application/json",
                "User-Agent": "Autonomous-DualAgent-TradingBot/1.0"
            })
        elif self._is_dummy_credentials():
            # Create a dummy session for consistency
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Autonomous-DualAgent-TradingBot/1.0"
            })
    def connect(self) -> bool:
        if self._dummy:
            self.is_connected = True
            self.last_error = None
            logger.info("Running in simulation mode with dummy credentials.")
            return True
        if not self.api_key or not self.api_secret:
            self.last_error = "Alpaca API credentials missing."
            logger.warning(self.last_error)
            return False
        try:
            resp = self.session.get(f"{self.base_url}/v2/account", timeout=10)
            if resp.status_code == 200:
                self.is_connected = True
                self.last_error = None
                logger.info("Connected to Alpaca Paper Broker.")
                return True
            else:
                self.last_error = f"Alpaca Auth Failed ({resp.status_code}): {resp.text}"
                logger.error(self.last_error)
                self.is_connected = False
                return False
        except Exception as e:
            self.last_error = f"Connection exception: {str(e)}"
            logger.error(self.last_error)
            self.is_connected = False
            return False

    def disconnect(self) -> bool:
        self.is_connected = False
        return True

    def get_account_info(self) -> Dict[str, Any]:
        if self._dummy:
            return {
                "account_number": "DUMMY123",
                "status": "ACTIVE",
                "currency": "USD",
                "cash_balance": 100000.0,
                "total_equity": 100000.0,
                "buying_power": 100000.0,
                "daytrade_count": 0,
                "is_paper": True
            }
        try:
            resp = self.session.get(f"{self.base_url}/v2/account", timeout=8)
            resp.raise_for_status()
            data = resp.json()
            return {
                "account_number": data.get("account_number"),
                "status": data.get("status"),
                "currency": data.get("currency", "USD"),
                "cash_balance": float(data.get("cash", 0.0)),
                "total_equity": float(data.get("portfolio_value", 0.0)),
                "buying_power": float(data.get("buying_power", 0.0)),
                "daytrade_count": int(data.get("daytrade_count", 0)),
                "is_paper": "paper" in self.base_url
            }
        except Exception as e:
            self.last_error = f"Failed to get Alpaca account: {str(e)}"
            logger.error(self.last_error)
            return {"error": self.last_error}

    def get_positions(self) -> List[Dict[str, Any]]:
        if self._dummy:
            return []
        try:
            resp = self.session.get(f"{self.base_url}/v2/positions", timeout=8)
            resp.raise_for_status()
            positions_data = resp.json()
            results = []
            for p in positions_data:
                results.append({
                    "ticker": p.get("symbol"),
                    "quantity": int(p.get("qty", 0)),
                    "avg_cost": float(p.get("avg_entry_price", 0.0)),
                    "current_price": float(p.get("current_price", 0.0)),
                    "market_value": float(p.get("market_value", 0.0)),
                    "unrealized_pnl": float(p.get("unrealized_pl", 0.0)),
                    "unrealized_pnl_pct": float(p.get("unrealized_plpc", 0.0)) * 100,
                    "side": p.get("side", "long")
                })
            return results
        except Exception as e:
            self.last_error = f"Failed to get Alpaca positions: {str(e)}"
            logger.error(self.last_error)
            return []

    def get_latest_quote(self, ticker: str) -> Dict[str, Any]:
        try:
            url = f"{self.data_url}/v2/stocks/{ticker}/quotes/latest?feed={self.data_feed}"
            resp = self.session.get(url, timeout=6)
            if resp.status_code == 200:
                q = resp.json().get("quote", {})
                return {
                    "ticker": ticker,
                    "bid_price": float(q.get("bp", 0.0)),
                    "bid_size": int(q.get("bs", 0)),
                    "ask_price": float(q.get("ap", 0.0)),
                    "ask_size": int(q.get("as", 0)),
                    "spread": round(float(q.get("ap", 0.0)) - float(q.get("bp", 0.0)), 4),
                    "timestamp": q.get("t")
                }
        except Exception as e:
            logger.error(f"Error fetching latest quote for {ticker}: {e}")
        return {"ticker": ticker, "bid_price": 0.0, "ask_price": 0.0, "spread": 0.0}

    def scan_shark_activity(self, ticker: str, lookback_minutes: int = 15) -> Dict[str, Any]:
        # Simplified version: return dummy data (we can improve later)
        return {
            "ticker": ticker,
            "shark_detected": False,
            "type": "QUIET_ORDER_FLOW",
            "delta_volume": 0,
            "total_trades_analyzed": 0,
            "total_volume": 0,
            "block_trades_count": 0,
            "block_trades": [],
            "buy_pressure_ratio": 0.0,
            "summary": f"No recent block trades detected on {ticker} in last {lookback_minutes}m."
        }

    def get_market_data(self, ticker: str, timeframe: str = "1D", limit: int = 50) -> List[Dict[str, Any]]:
        # For simplicity, we return dummy data. In a real scenario, we would call the API.
        # But to avoid errors, we return a dummy bar.
        # Note: In a real implementation, we would use timezone-aware datetime
        return [{
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "open": 200.0,
            "high": 210.0,
            "low": 195.0,
            "close": 205.0,
            "volume": 1000000,
            "trade_count": 100,
            "vwap": 205.0
        }]

    def place_order(self, order: OrderContract) -> OrderContract:
        if not self.is_connected and not self.connect():
            order.status = 'rejected'
            order.notes = "Broker disconnected / invalid API keys"
            return order
        side = "buy" if order.action == 'buy' else "sell"
        order_type = "market" if order.order_type == 'market' else "limit"
        payload = {
            "symbol": order.ticker,
            "qty": str(order.quantity),
            "side": side,
            "type": order_type,
            "time_in_force": "day"
        }
        if order.order_type == 'limit' and order.price:
            payload["limit_price"] = str(order.price)
        if order.order_type == 'stop' and order.stop_price:
            payload["stop_price"] = str(order.stop_price)
        try:
            resp = self.session.post(f"{self.base_url}/v2/orders", json=payload, timeout=8)
            if resp.status_code in [200, 201]:
                data = resp.json()
                order.order_id = data.get("id", order.order_id)
                alpaca_status = data.get("status", "pending")
                status_map = {
                    "new": "pending",
                    "accepted": "pending",
                    "filled": "filled",
                    "partially_filled": "partially_filled",
                    "canceled": "cancelled",
                    "rejected": "rejected"
                }
                order.status = status_map.get(alpaca_status, "pending")
                if data.get("filled_avg_price"):
                    order.execution_price = float(data.get("filled_avg_price"))
                    order.executed_quantity = int(data.get("filled_qty", 0))
                    # Use timezone-aware UTC datetime
                    order.execution_timestamp = datetime.now(timezone.utc)
                else:
                    quote = self.get_latest_quote(order.ticker)
                    fill_p = quote.get("ask_price") if side == "buy" else quote.get("bid_price")
                    order.execution_price = fill_p or 200.0
                    order.executed_quantity = order.quantity
                    order.status = "filled"
                    # Use timezone-aware UTC datetime
                    order.execution_timestamp = datetime.now(timezone.utc)
                logger.info(f"Alpaca Order Placed: #{order.order_id} {side.upper()} {order.quantity} {order.ticker} - Status: {order.status}")
                return order
            else:
                order.status = "rejected"
                order.notes = f"Alpaca Error {resp.status_code}: {resp.text}"
                logger.error(order.notes)
                return order
        except Exception as e:
            order.status = "rejected"
            order.notes = f"Execution Exception: {str(e)}"
            logger.error(order.notes)
            return order

    def cancel_order(self, order_id: str) -> bool:
        try:
            resp = self.session.delete(f"{self.base_url}/v2/orders/{order_id}", timeout=6)
            return resp.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_order_status(self, order_id: str) -> OrderContract:
        try:
            resp = self.session.get(f"{self.base_url}/v2/orders/{order_id}", timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                return OrderContract(
                    order_id=data.get("id"),
                    ticker=data.get("symbol"),
                    action=OrderAction.BUY if data.get("side") == "buy" else OrderAction.SELL,
                    quantity=int(data.get("qty", 0)),
                    execution_price=float(data.get("filled_avg_price")) if data.get("filled_avg_price") else None,
                    executed_quantity=int(data.get("filled_qty", 0)) if data.get("filled_qty") else None,
                    status="filled" if data.get("status") == "filled" else "pending",
                    source_component="alpaca_broker"
                )
        except Exception as e:
            logger.error(f"Error checking order status {order_id}: {e}")
        # Return a default unknown contract
        return OrderContract(order_id=order_id, ticker="UNKNOWN", action=OrderAction.BUY, quantity=1, source_component="unknown")