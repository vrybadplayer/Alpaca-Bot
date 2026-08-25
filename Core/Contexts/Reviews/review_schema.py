#!/usr/bin/env python3
"""
PnL Review Schema - Pydantic model for validating PnL review JSON files.
"""

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Dict, Optional, Any

class PnLReview(BaseModel):
    """Schema for PnL review JSON files."""
    timestamp: str = Field(..., description="ISO 8601 timestamp of when the review was generated")
    ticker: str = Field(..., description="Stock symbol")
    action: str = Field(..., description="Buy or sell action")
    quantity: int = Field(..., description="Number of shares traded")
    entry_price: float = Field(..., description="Price at which position was opened")
    exit_price: float = Field(..., description="Price at which position was closed")
    realized_pnl: float = Field(..., description="Realized profit and loss amount")
    return_pct: float = Field(..., description="Return percentage")
    is_profit: bool = Field(..., description="Whether the trade was profitable")
    reason: str = Field(..., description="Brief explanation of outcome")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    review_id: str = Field(..., description="Unique identifier for referencing")
    
    class Config:
        """Allow generation by parsing of extra fields."""
        extra = "allow"