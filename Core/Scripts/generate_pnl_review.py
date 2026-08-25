#!/usr/bin/env python3
"""
PnL Review Generator - creates JSON review files after trade execution.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

def generate_pnl_review(
    ticker: str,
    action: str,
    entry_price: float,
    exit_price: float,
    quantity: int,
    realized_pnl: float,
    reason: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate a PnL review in JSON format for criticism and future learning.
    
    Args:
        ticker: Stock symbol
        action: 'buy' or 'sell' 
        entry_price: Price at which position was opened
        exit_price: Price at which position was closed
        quantity: Number of shares traded
        realized_pnl: Profit and loss amount (positive = profit, negative = loss)
        reason: Brief explanation of outcome
        metadata: Optional additional context (e.g., strategy, market conditions)
        
    Returns:
        Dictionary representing the PnL review in JSON-serializable format
    """
    # Calculate return percentage
    if entry_price > 0:
        return_pct = (exit_price - entry_price) / entry_price * 100
    else:
        return_pct = 0.0
    
    # Determine if it was a profit or loss
    is_profit = realized_pnl >= 0
    
    # Create structured review
    review: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticker": ticker,
        "action": action,
        "quantity": quantity,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "realized_pnl": realized_pnl,
        "return_pct": return_pct,
        "is_profit": is_profit,
        "reason": reason,
        "metadata": metadata or {},
        # Generate a unique ID for referencing
        "review_id": f"review_{ticker}_{int(datetime.now().timestamp())}"
    }
    
    return review

if __name__ == "__main__":
    # Example usage
    example_review = generate_pnl_review(
        ticker="NVDA",
        action="sell",
        entry_price=200.0,
        exit_price=210.0,
        quantity=100,
        realized_pnl=1000.0,
        reason="Sold above target after strong earnings report",
        metadata={
            "strategy": "Momentum trading",
            "market_condition": "Bullish",
            "risk_reward_ratio": 2.0
        }
    )
    
    # Print to stdout for verification
    print(json.dumps(example_review, indent=2))
    
    # Save to file
    os.makedirs("reviews", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reviews/pnl_review_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(example_review, f, indent=2)
    print(f"Review saved to {filename}")