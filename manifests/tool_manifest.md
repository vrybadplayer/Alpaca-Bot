# Worker-Critic Tool Manifest

This manifest describes the available tools in the Worker-Critic system for use by the LLM agents.

## Available Tool Categories:

### Alpaca Tools (8):
- `alpaca.get_account_info`: Fetch real account balances, cash, buying power, and portfolio value from Alpaca.
- `alpaca.get_positions`: Fetch open positions from Alpaca.
- `alpaca.get_latest_quote`: Get the latest Level 1 Top of Book quote (Bid, Ask, Bid Size, Ask Size).
- `alpaca.scan_shark_activity`: Detect institutional footprints: whale block trades, aggressor order flow, cumulative volume delta (CVD), liquidity sweeps.
- `alpaca.get_market_data`: Get OHLCV historical candlestick bars from Alpaca Market Data v2.
- `alpaca.place_order`: Place a real paper order with Alpaca Markets API.
- `alpaca.cancel_order`: Cancel an open order on Alpaca.
- `alpaca.get_order_status`: Fetch current order status by Alpaca order ID.

### Worker Tools (6):
- `worker.fetch_market_data`: Fetch market data for a given ticker.
- `worker.calculate_technical_indicator`: Calculate a technical indicator for a given ticker.
- `worker.execute_order`: Execute a buy or sell order in the paper trading sandbox.
- `worker.get_portfolio`: Retrieve current portfolio state including cash, positions, and P&L.
- `worker.check_trade_risk`: Validate a proposed trade against risk invariants.
- `worker.generate_signal`: Generate a trade signal using the Researcher Persona.

### Critic Tools (7):
- `critic.analyze_market_psychology`: Analyze market sentiment, fear/greed indices, and behavioral patterns using DeepSeek-R1 and ChromaDB.
- `critic.audit_proposed_signal`: Deep Chain-of-Thought risk audit of a proposed trade signal from Worker Agent.
- `critic.detect_market_regime`: Identify the current macro market regime based on key indicators.
- `critic.analyze_risk_scenarios`: Performs stress testing and scenario analysis on a proposed trade or portfolio.
- `critic.validate_trade_signal`: Validates an executed trade against the original signal and checks for slippage, fees, and adherence.
- `critic.query_knowledge_base`: Queries the embedded ChromaDB vector store for relevant market psychology, regime indicators, or historical cases.
- `critic.conduct_post_mortem_autopsy`: Conduct a DeepSeek-R1 Post-Mortem Autopsy on a losing or stopped-out trade.

### Utility Tools (5):
- `utility.load_persona`: Load a persona markdown file for LLM prompting.
- `utility.load_manifest`: Load a tool manifest markdown file for LLM prompting.
- `utility.chat_with_ollama`: Send a chat message to the Ollama LLM.
- `utility.vector_store_query`: Query the vector store for similar vectors using query_knowledge method.
- `utility.vector_store_add_text`: Add a text document to the vector store.

## Usage Guidelines:
1. Always load the appropriate persona before generating or auditing signals
2. Use the critic to audit all worker-generated signals before execution
3. Check trade risk using the worker's risk validation tool before placing orders
4. Maintain proper position sizing and risk management practices