# Trading Rules

## Core Risk Management Principles

1. **Stop-Loss Requirement**: Every trade MUST have a defined stop-loss level.
2. **Take-Profit Recommendation**: Every trade SHOULD have a defined take-profit level.
3. **Position Sizing**: No single trade should risk more than 2% of the total account equity.
4. **Maximum Daily Loss**: Stop trading for the day if losses exceed 5% of starting equity.
5. **Shark Activity Protocol**: 
   - If shark activity is detected (large block trades, aggressive order flow), reduce position size by 50% or halt new entries.
   - If shark activity indicates accumulation (buying pressure), consider increasing position size cautiously.
   - If shark activity indicates distribution (selling pressure), consider reducing exposure or tightening stops.
6. **Risk-Reward Ratio**: Minimum acceptable risk-reward ratio is 1:2 (potential profit should be at least twice the potential loss).
7. **Market Hours**: Only trade during regular market hours (9:30 AM - 4:00 PM EST) unless otherwise specified.
8. **News Events**: Avoid opening new positions 15 minutes before major economic news releases.
9. **Maximum Concurrent Positions**: Limit to 5 open positions at any time.
10. **Trailing Stops**: Consider using trailing stops for winning trades to lock in profits.

## Specific Rules for NVDA Trading

1. **Volatility Adjustment**: Due to NVDA's higher volatility, use wider stop-losses (minimum 2% from entry) and consider scaling in/out of positions.
2. **Earnings Sensitivity**: Reduce position size by 50% during the week of earnings announcements.
3. **Technical Confluence**: Require at least two technical indicators to agree before entering a trade.
4. **Volume Confirmation**: Ensure trades are supported by above-average volume.

## Enforcement

- All trades must be reviewed by the Risk Management system before execution.
- Violations of these rules will result in trade rejection or automatic adjustment.
- The Risk Management system has the authority to override trade signals from the Worker or Critic if necessary to comply with these rules.