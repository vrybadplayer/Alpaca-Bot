#!/usr/bin/env python3
"""
Generator Worker (System 1) implementation.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from Core.Alpaca.alpaca_broker import AlpacaBroker
from Core.Tool_Registry.utils import VectorStore, OllamaClient, PortfolioManager, OrderContract, OrderAction, OrderType, TradeSignal

logger = logging.getLogger(__name__)

class GeneratorWorker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        broker_cfg = config.get('broker', {})
        self.broker = AlpacaBroker(broker_cfg)
        self.min_cash_reserve = config.get('system', {}).get('cash_reserve', 5000.0)
        self.position_tracker = PortfolioManager(initial_cash=broker_cfg.get('sandbox_initial_balance', 100000.0), reserve_limit=self.min_cash_reserve)
        self.vector_store = VectorStore()
        self.llm_client = OllamaClient(base_url=config.get('model_routing', {}).get('ollama_base_url', 'http://localhost:11434'))
        self.worker_model = config.get('model_routing', {}).get('worker_engine', {}).get('primary', 'qwen2.5-coder:7b')
        self.tickers = config.get('tickers', ['NVDA'])
        self.timeframe = config.get('timeframe', '1D')
        self.lookback_period = config.get('lookback_period', 20)
        logger.info(f"Generator Worker initialized (Model: {self.worker_model})")

    def fetch_market_data(self, ticker: str, timeframe: str = None, limit: int = 100) -> Dict[str, Any]:
        timeframe = timeframe or self.timeframe
        data = self.broker.get_market_data(ticker, timeframe, limit)
        if not data:
            return {"error": "Failed to fetch market data", "status": "error"}
        return {
            "ticker": ticker,
            "timeframe": timeframe,
            "data": data,
            "count": len(data),
            "status": "success"
        }

    def calculate_technical_indicator(self, ticker: str, indicator: str, timeframe: str = None, period: int = None, apply_to: str = "close") -> Dict[str, Any]:
        # Stub: return dummy values (we can improve later)
        return {
            "ticker": ticker,
            "indicator": indicator,
            "timeframe": timeframe or self.timeframe,
            "period": period or 14,
            "values": [{"timestamp": datetime.now(timezone.utc).isoformat(), "value": 50.0}],
            "status": "success"
        }

    def execute_order(self, ticker: str, action: str, quantity: int, order_type: str = "MARKET", price: float = None, stop_price: float = None) -> Dict[str, Any]:
        if action not in ["BUY", "SELL"]:
            return {"error": "Action must be BUY or SELL", "status": "error"}
        if quantity <= 0:
            return {"error": "Quantity must be positive", "status": "error"}
        order_action = OrderAction.BUY if action == "BUY" else OrderAction.SELL
        order_type_enum = OrderType.MARKET
        if order_type == "LIMIT":
            order_type_enum = OrderType.LIMIT
        elif order_type == "STOP":
            order_type_enum = OrderType.STOP
        elif order_type == "STOP_LIMIT":
            order_type_enum = OrderType.STOP_LIMIT
        order = OrderContract(
            ticker=ticker,
            action=order_action,
            quantity=quantity,
            order_type=order_type_enum,
            price=price,
            stop_price=stop_price,
            source_component="generator_worker"
        )
        executed_order = self.broker.place_order(order)
        if executed_order.status == "rejected":
            return {"error": executed_order.notes, "status": "error"}
        return {
            "order_id": executed_order.order_id,
            "ticker": executed_order.ticker,
            "action": executed_order.action.value,
            "quantity": executed_order.executed_quantity,
            "order_type": executed_order.order_type.value,
            "execution_price": executed_order.execution_price,
            "timestamp": executed_order.execution_timestamp.isoformat() + "Z" if executed_order.execution_timestamp else None,
            "status": executed_order.status.value,
            "fees": executed_order.fees,
            "slippage": executed_order.slippage
        }

    def get_portfolio(self) -> Dict[str, Any]:
        state = self.position_tracker.get_state()
        return {
            "cash_balance": state.cash_balance,
            "total_equity": state.total_equity,
            "realized_pnl": state.realized_pnl,
            "unrealized_pnl": state.unrealized_pnl,
            "positions": [
                {
                    "ticker": pos.ticker,
                    "quantity": pos.quantity,
                    "avg_cost": pos.avg_cost,
                    "current_price": pos.current_price,
                    "market_value": pos.market_value,
                    "unrealized_pnl": pos.unrealized_pnl
                }
                for pos in state.positions
            ],
            "status": "success"
        }

    def check_trade_risk(self, ticker: str, action: str, quantity: int, price: float) -> Dict[str, Any]:
        if action not in ["BUY", "SELL"]:
            return {"error": "Action must be BUY or SELL", "status": "error"}
        if quantity <= 0:
            return {"error": "Quantity must be positive", "status": "error"}
        if price <= 0:
            return {"error": "Price must be positive", "status": "error"}
        state = self.position_tracker.get_state()
        trade_value = quantity * price
        violations = []
        adjusted_quantity = quantity
        if action == "BUY":
            trade_cost = trade_value
            available_cash = state.cash_balance - state.reserve_limit
            if trade_cost > available_cash:
                violations.append("cash_reserve")
                if price > 0:
                    adjusted_quantity = int(available_cash / price)
            position_value = trade_value
            total_equity_after = state.total_equity
            position_pct = position_value / total_equity_after if total_equity_after > 0 else 0
            max_position_pct = 0.1
            if position_pct > max_position_pct:
                violations.append("position_size")
                if price > 0:
                    max_position_value = total_equity_after * max_position_pct
                    adjusted_quantity = min(adjusted_quantity, int(max_position_value / price))
        elif action == "SELL":
            current_position = 0
            for pos in state.positions:
                if pos.ticker == ticker:
                    current_position = pos.quantity
                    break
            if current_position < quantity:
                violations.append("insufficient_position")
                adjusted_quantity = current_position
        approved = len(violations) == 0
        return {
            "approved": approved,
            "violations": violations,
            "adjusted_quantity": max(0, adjusted_quantity),
            "reason": "Trade complies with all risk invariants" if approved else f"Violations: {', '.join(violations)}",
            "status": "success"
        }

    def generate_signal(self, ticker: str) -> Optional[TradeSignal]:
        # Use the researcher persona to generate a signal
        try:
            # Load the researcher persona
            persona_content = self.llm_client.load_persona("researcher")
            
            # Create a prompt for signal generation
            messages = [
                {
                    "role": "user",
                    "content": f"Generate a trade signal for {ticker} based on current market conditions. Provide action (BUY/SELL), quantity, target price, stop loss, take profit, and confidence level."
                }
            ]
            
            # Get response from LLM with researcher persona
            response = self.llm_client.chat(
                model=self.worker_model,
                messages=messages,
                temperature=0.1,
                format_json=True,
                persona="researcher"
            )
            
            if response.get("status") == "success" and "json_data" in response:
                data = response["json_data"]
                action_str = data.get("action", "HOLD")
                if action_str in ["BUY", "SELL"]:
                    return TradeSignal(
                        ticker=ticker,
                        action=OrderAction.BUY if action_str == "BUY" else OrderAction.SELL,
                        quantity=int(data.get("suggested_quantity", 100)),
                        target_price=float(data.get("target_price", 200.0)),
                        stop_loss=float(data.get("stop_loss", 190.0)),
                        take_profit=float(data.get("take_profit", 210.0)),
                        confidence=float(data.get("confidence", 0.7)),
                        timestamp=datetime.now(timezone.utc),
                        source="worker_with_researcher_persona",
                        rationale=data.get("thesis", "Signal generated using researcher persona")
                    )
        except Exception as e:
            logger.warning(f"Failed to generate signal using LLM: {e}")
        
        # Fallback to stub signal generation
        import random
        if random.random() > 0.7:
            return TradeSignal(
                ticker=ticker,
                action=OrderAction.BUY if random.random() > 0.5 else OrderAction.SELL,
                quantity=100,
                target_price=200.0,
                stop_loss=190.0,
                take_profit=210.0,
                confidence=0.7,
                timestamp=datetime.now(timezone.utc),
                source="worker_stub",
                rationale="Stub signal"
            )
        return None