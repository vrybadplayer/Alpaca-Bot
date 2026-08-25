#!/usr/bin/env python3
"""
Risk Manager implementation for checking trades against trading rules and providing risk assessments.
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from Core.alpaca_broker import AlpacaBroker
from Core.utils import VectorStore, OllamaClient, PortfolioManager, OrderContract, OrderAction, OrderType, TradeSignal

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        broker_cfg = config.get('broker', {})
        self.broker = AlpacaBroker(broker_cfg)
        self.min_cash_reserve = config.get('system', {}).get('cash_reserve', 5000.0)
        self.position_tracker = PortfolioManager(initial_cash=broker_cfg.get('sandbox_initial_balance', 100000.0), reserve_limit=self.min_cash_reserve)
        self.vector_store = VectorStore()
        self.llm_client = OllamaClient(base_url=config.get('model_routing', {}).get('ollama_base_url', 'http://localhost:11434'))
        self.risk_manager_model = config.get('model_routing', {}).get('risk_manager_engine', {}).get('primary', 'qwen2.5-coder:7b')
        self.tickers = config.get('tickers', ['NVDA'])
        self.lookback_days = config.get('lookback_days', 30)
        # Load trading rules (for now, we hardcode; in the future, we can parse the markdown file)
        self.trading_rules = self._load_trading_rules()
        logger.info(f"Risk Manager initialized (Model: {self.risk_manager_model})")

    def _load_trading_rules(self) -> Dict[str, Any]:
        """
        Load trading rules from the trading_rules.md file.
        For simplicity, we return a hardcoded dictionary of rules.
        In a more advanced version, we would parse the markdown file.
        """
        # In the future, we can read and parse the file at /c/VS Code/Alpaca-Bot/trading_rules.md
        # For now, we return a set of rules as a dictionary.
        return {
            "stop_loss_required": True,
            "take_profit_recommended": True,
            "max_risk_per_trade": 0.02,  # 2% of account equity
            "max_daily_loss": 0.05,      # 5% of starting equity
            "shark_activity_threshold": {
                "reduce_position": 0.5,  # Reduce position by 50% if shark activity detected
                "halt_new_entries": False
            },
            "min_risk_reward_ratio": 2.0,  # 1:2 (reward:risk)
            "market_hours_only": True,
            "avoid_news_events_minutes": 15,
            "max_concurrent_positions": 5,
            "use_trailing_stops": True,
            # NVDA specific rules
            "nvda_volatility_adjustment": {
                "min_stop_loss_pct": 0.02,  # 2% minimum stop-loss for NVDA
                "earnings_week_reduction": 0.5  # Reduce position by 50% during earnings week
            }
        }

    def check_trade_signal(self, signal: TradeSignal, current_price: float) -> Dict[str, Any]:
        """
        Check a trade signal against the trading rules.
        Returns a dictionary with approval status, violations, adjusted quantity, and reason.
        """
        if signal.action not in [OrderAction.BUY, OrderAction.SELL]:
            return {"error": "Action must be BUY or SELL", "status": "error"}
        if signal.quantity <= 0:
            return {"error": "Quantity must be positive", "status": "error"}
        if signal.target_price <= 0 or signal.stop_loss <= 0 or signal.take_profit <= 0:
            return {"error": "Prices must be positive", "status": "error"}

        state = self.position_tracker.get_state()
        violations = []
        adjusted_quantity = signal.quantity

        # Rule 1: Stop-loss required
        if self.trading_rules["stop_loss_required"]:
            if signal.action == OrderAction.BUY:
                if signal.stop_loss >= signal.target_price:
                    violations.append("stop_loss_not_below_target_for_buy")
            else:  # SELL
                if signal.stop_loss <= signal.target_price:
                    violations.append("stop_loss_not_above_target_for_sell")

        # Rule 2: Take-profit recommended (we'll just warn, not violate)
        if self.trading_rules["take_profit_recommended"]:
            if signal.action == OrderAction.BUY:
                if signal.take_profit <= signal.target_price:
                    # This is a violation for a buy: take profit should be above target
                    violations.append("take_profit_not_above_target_for_buy")
            else:  # SELL
                if signal.take_profit >= signal.target_price:
                    violations.append("take_profit_not_below_target_for_sell")

        # Rule 3: Position sizing (max risk per trade)
        # Risk per trade = quantity * |entry_price - stop_loss|
        # We'll use the target_price as the entry price for this check (or we could use current_price?)
        # Let's use the target_price as the intended entry.
        risk_per_share = abs(signal.target_price - signal.stop_loss)
        total_risk = risk_per_share * signal.quantity
        max_risk_amount = state.total_equity * self.trading_rules["max_risk_per_trade"]
        if total_risk > max_risk_amount:
            violations.append("exceeds_max_risk_per_trade")
            if risk_per_share > 0:
                adjusted_quantity = int(max_risk_amount / risk_per_share)
            else:
                adjusted_quantity = 0

        # Rule 4: Risk-reward ratio
        # For a buy: reward = take_profit - target_price, risk = target_price - stop_loss
        # For a sell: reward = target_price - take_profit, risk = stop_loss - target_price
        if signal.action == OrderAction.BUY:
            reward = signal.take_profit - signal.target_price
            risk = signal.target_price - signal.stop_loss
        else:  # SELL
            reward = signal.target_price - signal.take_profit
            risk = signal.stop_loss - signal.target_price

        if risk <= 0:
            violations.append("invalid_risk_in_risk_reward_calculation")
        else:
            risk_reward_ratio = reward / risk
            if risk_reward_ratio < self.trading_rules["min_risk_reward_ratio"]:
                violations.append("risk_reward_ratio_below_minimum")
                # Adjust quantity to meet the minimum risk-reward ratio? 
                # Instead, we can adjust the stop-loss or take-profit, but for simplicity, we'll just flag it.
                # We don't adjust quantity for risk-reward ratio in this simple implementation.

        # Rule 5: Shark activity check (we'll check via the broker's shark activity scan)
        # We'll do a quick scan for the ticker
        shark_scan = self.broker.scan_shark_activity(signal.ticker, lookback_minutes=15)
        if shark_scan.get("shark_detected", False):
            # According to rules, we reduce position by 50% or halt new entries.
            # We'll reduce the position by 50% for now.
            violations.append("shark_activity_detected")
            adjusted_quantity = int(adjusted_quantity * self.trading_rules["shark_activity_threshold"]["reduce_position"])

        # Rule 6: NVDA specific rules (if ticker is NVDA)
        if signal.ticker == "NVDA":
            # Check if we are in the week of earnings (we don't have earnings data, so we skip for now)
            # We'll just apply the volatility adjustment for stop-loss min.
            if signal.action == OrderAction.BUY:
                min_stop_loss = signal.target_price * (1 - self.trading_rules["nvda_volatility_adjustment"]["min_stop_loss_pct"])
                if signal.stop_loss > min_stop_loss:
                    # The stop-loss is too tight (too close to the target) for NVDA's volatility
                    violations.append("stop_loss_too_tight_for_nvda_volatility")
                    # Adjust the stop-loss to be at least the minimum
                    # We don't adjust the stop-loss in the signal here because we are only adjusting quantity.
                    # Instead, we note the violation and let the user know.
            else:  # SELL
                min_stop_loss = signal.target_price * (1 + self.trading_rules["nvda_volatility_adjustment"]["min_stop_loss_pct"])
                if signal.stop_loss < min_stop_loss:
                    violations.append("stop_loss_too_tight_for_nvda_volatility")

        # Rule 7: Maximum concurrent positions
        current_positions = 0
        for pos in state.positions:
            if pos.ticker == signal.ticker:
                current_positions += pos.quantity
        if current_positions + adjusted_quantity > self.trading_rules["max_concurrent_positions"]:
            violations.append("would_exceed_max_concurrent_positions")
            adjusted_quantity = max(0, self.trading_rules["max_concurrent_positions"] - current_positions)

        # Ensure adjusted_quantity is non-negative
        adjusted_quantity = max(0, adjusted_quantity)

        approved = len(violations) == 0
        return {
            "approved": approved,
            "violations": violations,
            "adjusted_quantity": adjusted_quantity,
            "reason": "Trade complies with all risk management rules" if approved else f"Violations: {', '.join(violations)}",
            "status": "success"
        }

    def assess_risk_with_llm(self, signal: TradeSignal, current_price: float, market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Use the LLM with the finance-investment-researcher persona to provide a risk assessment.
        """
        try:
            # Load the finance-investment-researcher persona
            persona_content = self.llm_client.load_persona("finance-investment-researcher")
            
            # Create a prompt for risk assessment
            messages = [
                {
                    "role": "user",
                    "content": f"""
                    Assess the risk of this trade signal:
                    Ticker: {signal.ticker}
                    Action: {signal.action}
                    Quantity: {signal.quantity}
                    Target Price: {signal.target_price}
                    Stop Loss: {signal.stop_loss}
                    Take Profit: {signal.take_profit}
                    Current Price: {current_price}
                    Confidence: {signal.confidence}
                    
                    Provide a risk assessment including:
                    - Overall risk level (low, medium, high)
                    - Key risk factors
                    - Suggested adjustments (if any)
                    - Whether the trade should be taken as-is, adjusted, or rejected
                    """,
                }
            ]
            
            # Get response from LLM with the finance-investment-researcher persona
            response = self.llm_client.chat(
                model=self.risk_manager_model,
                messages=messages,
                temperature=0.1,
                format_json=True,
                persona="finance-investment-researcher"
            )
            
            if response.get("status") == "success" and "json_data" in response:
                data = response["json_data"]
                return {
                    "risk_assessment": data.get("assessment", "No assessment provided"),
                    "risk_level": data.get("risk_level", "medium"),
                    "key_risk_factors": data.get("key_risk_factors", []),
                    "suggested_adjustments": data.get("suggested_adjustments", []),
                    "recommendation": data.get("recommendation", "hold"),
                    "thinking": response.get("thinking", "Stub thinking"),
                    "status": "success"
                }
            else:
                logger.warning("LLM did not return expected JSON for risk assessment")
                return {"error": "LLM did not return expected JSON", "status": "error"}
        except Exception as e:
            logger.warning(f"Failed to assess risk using LLM: {e}")
            logger.warning(traceback.format_exc())
            return {"error": str(e), "status": "error"}