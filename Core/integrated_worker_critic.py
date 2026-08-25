#!/usr/bin/env python3
"""
Main script for the integrated Worker-Critic system with Alpaca tool registration.
This script uses dependency injection to wire all components together.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env in the Alpaca-Bot root (project root)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

# Import our modules
from Core.Setups.container import load_config_from_env, Container

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("=" * 60)
    print("Integrated Worker-Critic with Alpaca Tool Registration")
    print("=" * 60)

    try:
        # Load configuration
        print("\n1. Loading configuration...")
        config = load_config_from_env()
        
        # Validate required configuration
        if not config.get('ALPACA_API_KEY') or not config.get('ALPACA_SECRET_KEY'):
            raise ValueError("Alpaca API credentials not found in environment variables")
        
        print("   ✓ Configuration loaded successfully")

        # Create dependency injection container
        print("\n2. Creating dependency injection container...")
        container = Container(config)
        print("   ✓ Container created")

        # Initialize Alpaca Broker
        print("\n3. Initializing Alpaca Broker...")
        broker = container.get_alpaca_broker()
        if not broker.connect():
            raise ConnectionError("Failed to connect to Alpaca Paper Trading API.")
        account_info = broker.get_account_info()
        print(f"   ✓ Connected to Alpaca Paper Trading")
        print(f"   Account: #{account_info.get('account_number')}")
        print(f"   Cash Balance: ${account_info.get('cash_balance', 0):,.2f}")
        print(f"   Total Equity: ${account_info.get('total_equity', 0):,.2f}")

        # Initialize LLM Client (Ollama)
        print("\n4. Initializing LLM Client (Ollama)...")
        llm_client = container.get_ollama_client()
        models = llm_client.get_available_models()
        print(f"   ✓ Ollama connected at {llm_client.base_url}")
        print(f"   Available models: {', '.join(models) if models else 'None'}")

        # Initialize Vector Store
        print("\n5. Initializing Vector Store...")
        vector_store = container.get_vector_store()
        print("   ✓ Vector store initialized")

        # Initialize Generator Worker (System 1)
        print("\n6. Initializing Generator Worker (System 1)...")
        worker = container.get_generator_worker()
        print("   ✓ Generator Worker initialized")
        print(f"   Model: {worker.worker_model}")
        print(f"   Tickers: {worker.tickers}")

        # Initialize Critic Auditor (System 2)
        print("\n7. Initializing Critic Auditor (System 2)...")
        critic = container.get_critic_auditor()
        print("   ✓ Critic Auditor initialized")

        # Initialize Risk Manager (System 3)
        print("\n8. Initializing Risk Manager (System 3)...")
        risk_manager = container.get_risk_manager()
        print("   ✓ Risk Manager initialized")

        # Get Tool Registry
        print("\n9. Getting Tool Registry...")
        tool_registry = container.get_tool_registry()
        tools = tool_registry.list_tools()
        print(f"   ✓ Tool registry ready with {len(tools)} tools")

        # Group tools by category for display
        categories = {}
        for tool in tools:
            cat = tool['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tool)

        print("\n10. Tool Summary:")
        for category, tool_list in categories.items():
            print(f"   {category.upper()} TOOLS ({len(tool_list)}):")
            for tool in tool_list:
                print(f"     - {tool['name']}: {tool['description']}")

        # Demonstrate a few key tools
        print("\n11. Demonstrating key tools...")

        # Get account info
        result = tool_registry.execute_tool('alpaca.get_account_info')
        if result['status'] == 'success':
            acc = result['result']
            print(f"   ✓ Alpaca Account Info: Cash=${acc.get('cash_balance', 0):,.2f}, Equity=${acc.get('total_equity', 0):,.2f}")

        # Get latest quote for NVDA
        result = tool_registry.execute_tool('alpaca.get_latest_quote', 'NVDA')
        if result['status'] == 'success':
            quote = result['result']
            print(f"   ✓ NVDA Quote: Bid=${quote.get('bid_price', 0):.2f}, Ask=${quote.get('ask_price', 0):.2f}")

        # Fetch market data for NVDA
        result = tool_registry.execute_tool('worker.fetch_market_data', 'NVDA', limit=5)
        if result['status'] == 'success':
            data = result['result']
            print(f"   ✓ Market Data: Retrieved {data.get('count', 0)} data points for NVDA")

        # Generate a signal (Worker) - now using researcher persona
        result = tool_registry.execute_tool('worker.generate_signal', 'NVDA')
        if result['status'] == 'success':
            signal = result['result']
            if signal:
                print(f"   ✓ Generated Signal: {signal.action} {signal.quantity} NVDA @ ${signal.target_price:.2f} (Conf: {signal.confidence:.2f})")
            else:
                print("   ℹ No signal generated (holding)")

        # Check the signal with the Risk Manager
        if signal:
            # We need the current price for the risk check
            quote_result = tool_registry.execute_tool('alpaca.get_latest_quote', 'NVDA')
            if quote_result['status'] == 'success':
                current_price = (quote_result['result'].get('bid_price', 0) + quote_result['result'].get('ask_price', 0)) / 2
                # Alternatively, we can use the last price or the close from market data, but for simplicity, we use the mid of bid/ask.
                # However, note that the signal already has a target_price, stop_loss, and take_profit.
                # We'll use the current price as the mid of bid/ask for the risk check.
                risk_check_result = tool_registry.execute_tool('risk.check_trade_signal', signal, current_price)
                if risk_check_result['status'] == 'success':
                    risk_check = risk_check_result['result']
                    print(f"   ✓ Risk Check: Approved={risk_check.get('approved')}, Violations={risk_check.get('violations')}, Adjusted Quantity={risk_check.get('adjusted_quantity')}")
                    print(f"       Reason: {risk_check.get('reason')}")
                else:
                    print(f"   ❌ Risk Check failed: {risk_check_result.get('error')}")
            else:
                print("   ❌ Could not get current price for risk check")
        else:
            print("   ℹ Skipping risk check because no signal was generated")

        # Assess risk with LLM (using the finance-investment-researcher persona) if we have a signal
        if signal:
            quote_result = tool_registry.execute_tool('alpaca.get_latest_quote', 'NVDA')
            if quote_result['status'] == 'success':
                current_price = (quote_result['result'].get('bid_price', 0) + quote_result['result'].get('ask_price', 0)) / 2
                # We can also fetch some market data for context, but for simplicity, we'll just use the current price.
                risk_assessment_result = tool_registry.execute_tool('risk.assess_risk_with_llm', signal, current_price)
                if risk_assessment_result['status'] == 'success':
                    risk_assessment = risk_assessment_result['result']
                    print(f"   ✓ LLM Risk Assessment: Recommendation={risk_assessment.get('recommendation')}, Risk Level={risk_assessment.get('risk_level')}")
                    print(f"       Key Risk Factors: {risk_assessment.get('key_risk_factors')}")
                    print(f"       Suggested Adjustments: {risk_assessment.get('suggested_adjustments')}")
                else:
                    print(f"   ❌ LLM Risk Assessment failed: {risk_assessment_result.get('error')}")
            else:
                print("   ❌ Could not get current price for LLM risk assessment")
        else:
            print("   ℹ Skipping LLM risk assessment because no signal was generated")

        # Scan for shark activity
        result = tool_registry.execute_tool('alpaca.scan_shark_activity', 'NVDA', lookback_minutes=15)
        if result['status'] == 'success':
            scan = result['result']
            print(f"   ✓ Shark Activity Scan: {scan.get('type')} (Delta: {scan.get('delta_volume'):+,d} shares)")

        print("\n" + "=" * 60)
        print("INTEGRATION COMPLETE")
        print("All Worker-Critic components and Alpaca tools are registered and ready.")
        print("Use the tool_registry.execute_tool('tool_name', *args) to invoke any tool.")
        print("=" * 60)

        return {
            'broker': broker,
            'worker': worker,
            'critic': critic,
            'risk_manager': risk_manager,
            'tool_registry': tool_registry,
            'llm_client': llm_client,
            'vector_store': vector_store,
            'container': container
        }

    except Exception as e:
        print(f"\n❌ Error during integration: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()