#!/usr/bin/env python3

"""
Critic Auditor (System 2) implementation.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from Core.Alpaca.alpaca_broker import AlpacaBroker
from Core.Tool_Registry.utils import VectorStore, OllamaClient, PortfolioManager, OrderContract, OrderAction, OrderType, TradeSignal
from Core.Contexts.Reviews.review_schema import PnLReview

logger = logging.getLogger(__name__)

class CriticAuditor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        broker_cfg = config.get('broker', {})
        self.broker = AlpacaBroker(broker_cfg)
        self.min_cash_reserve = config.get('system', {}).get('cash_reserve', 5000.0)
        self.position_tracker = PortfolioManager(initial_cash=broker_cfg.get('sandbox_initial_balance', 100000.0), reserve_limit=self.min_cash_reserve)
        self.transaction_ledger = None  # Stub for future implementation
        self.vector_store = VectorStore()
        self.llm_client = OllamaClient(base_url=config.get('model_routing', {}).get('ollama_base_url', 'http://localhost:11434'))
        self.critic_model = config.get('model_routing', {}).get('critic_engine', {}).get('primary', 'deepseek-r1:14b')
        self.tickers = config.get('tickers', ['NVDA'])
        self.lookback_days = config.get('lookback_days', 30)
        self._repo_root = Path(__file__).resolve().parents[2]  # repo root path for locating reviews
        logger.info(f"Critic Auditor initialized (Model: {self.critic_model})")

    def analyze_market_psychology(self, ticker: str = None, lookback_days: int = None, data_sources: List[str] = None) -> Dict[str, Any]:
        lookback_days = lookback_days or self.lookback_days
        data_sources = data_sources or ["social_media", "news", "options_flow"]
        return {
            "ticker": ticker or "MARKET",
            "sentiment_score": 0.0,
            "dominant_emotion": "neutral",
            "detected_patterns": [],
            "confidence": 0.8,
            "explanation": "Stub market psychology analysis",
            "status": "success"
        }

    def audit_proposed_signal(self, signal: TradeSignal, current_price: float) -> Dict[str, Any]:
        # Use the critic persona to audit the signal
        try:
            # Load the critic persona (we'll create a basic one for now)
            persona_content = self.llm_client.load_persona("critic")
            
            # Create a prompt for signal audit
            messages = [
                {
                    "role": "user",
                    "content": f"Audit this trade signal: {signal.action.value} {signal.quantity} {signal.ticker} @ target ${signal.target_price:.2f}, stop ${signal.stop_loss:.2f}, profit ${signal.take_profit:.2f}, confidence {signal.confidence:.2f}. Current price: ${current_price:.2f}. Provide approval decision, any violations, adjusted quantity, and reasoning."
                }
            ]
            
            # Get response from LLM with critic persona
            response = self.llm_client.chat(
                model=self.critic_model,
                messages=messages,
                temperature=0.1,
                format_json=True,
                persona="critic"
            )
            
            if response.get("status") == "success" and "json_data" in response:
                data = response["json_data"]
                # For now, we'll use a simplified interpretation
                # In a real implementation, we would parse the JSON response more carefully
                approved = data.get("action", "HOLD") in ["BUY", "SELL"] and data.get("confidence", 0) > 0.5
                return {
                    "approved": approved,
                    "violations": [] if approved else ["Insufficient confidence from critic audit"],
                    "adjusted_quantity": signal.quantity if approved else 0,
                    "reason": data.get("thesis", "Critic audit completed"),
                    "thinking": response.get("thinking", "Stub thinking"),
                    "status": "success"
                }
        except Exception as e:
            logger.warning(f"Failed to audit signal using LLM: {e}")
        
        # Fallback to simplified audit
        approved = signal.quantity > 0
        return {
            "approved": approved,
            "violations": [] if approved else ["Insufficient quantity"],
            "adjusted_quantity": signal.quantity if approved else 0,
            "reason": "Stub audit: approved" if approved else "Stub audit: rejected",
            "thinking": "Stub thinking",
            "status": "success"
        }

    def detect_market_regime(self, indicators: List[str] = None, lookback_days: int = None) -> Dict[str, Any]:
        return {
            "regime": "neutral",
            "confidence": 0.7,
            "supporting_indicators": {"VIX": 20.0, "10Y_Yield": 4.0, "DXY": 100.0, "SPY_VOL": 0.2},
            "explanation": "Stub regime detection",
            "status": "success"
        }

    def analyze_risk_scenarios(self, portfolio: Dict[str, Any] = None, trade_proposal: Dict[str, Any] = None, scenarios: List[str] = None) -> Dict[str, Any]:
        scenarios = scenarios or ["market_crash", "liquidity_dry_up", "volatility_spike", "interest_rate_shock"]
        return {
            "portfolio_var_95": 1000.0,
            "expected_shortfall": 1500.0,
            "scenario_impacts": {s: {"portfolio_change_pct": -10.0, "new_cash_reserve": 50000.0, "passes_invariant": True, "required_reserve_floor": 5000.0} for s in scenarios},
            "recommendation": "Stub recommendation: trade passes all scenario tests",
            "status": "success"
        }

    def validate_trade_signal(self, signal: Dict[str, Any] = None, execution: Dict[str, Any] = None, market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        return {
            "adherence_score": 1.0,
            "slippage": 0.0,
            "fees": 0.0,
            "notes": "Stub validation: execution adhered closely to signal",
            "status": "success"
        }

    def load_recent_pnl_reviews(self, limit: int = 5):
        """Load recent PnL review JSON files and validate them."""
        import json
        from pathlib import Path
        review_dir = self._repo_root / "Core" / "Contexts" / "Reviews"
        if not review_dir.is_dir():
            logger.warning("PnL review directory not found: %s", review_dir)
            return []
        json_files = sorted(review_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        recent_files = json_files[:limit]
        validated_reviews = []
        for f in recent_files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                review = PnLReview(**data)
                validated_reviews.append(review.dict())
            except Exception as e:
                logger.warning("Failed to validate review %s: %s", f, e)
        return validated_reviews

    def receive_pnl_review(self, review: dict):
        """Store a PnL review for later use by the critic."""
        logger.info(
            f"PnL Review received: review_id={review.get('review_id')}, "
            f"ticker={review.get('ticker')}, realized_pnl={review.get('realized_pnl')}"
        )

    def store_review(self, review: dict):
        """Validate and store a PnL review for later analysis."""
        try:
            # Validate against PnLReview schema
            validated = PnLReview(**review)
            # Append to history, keep bounded
            self.pnl_history.append(validated.dict())
            if len(self.pnl_history) > 100:
                self.pnl_history.pop(0)
            logger.info(f"PnL Review stored: review_id={review.get('review_id')}")
        except Exception as e:
            logger.warning(f"Failed to store PnL review: {e}")

    def query_knowledge_base(self, query: str, n_results: int = 5, filter_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        return {
            "results": [],
            "count": 0,
            "status": "success"
        }

    def conduct_post_mortem_autopsy(self, failed_trade: Dict[str, Any], market_context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {
            "ticker": failed_trade.get("ticker", "UNKNOWN"),
            "loss_amount": failed_trade.get("loss_amount", 0.0),
            "loss_pct": failed_trade.get("loss_pct", 0.0),
            "root_cause": "Stub root cause",
            "breakdown": "Stub breakdown",
            "lesson_learned": "Stub lesson learned",
            "failure_tag": "STUB_FAILURE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chroma_embedded": False,
            "status": "success"
        }