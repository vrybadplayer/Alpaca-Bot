#!/usr/bin/env python3
"""
Integrated Worker-Critic Orchestration Script
Main script for the integrated Worker-Critic system with Alpaca tool registration.
This script uses dependency injection to wire all components together and
includes PnL Review processing for post‑trade learning.
"""

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ----------------------------------------------------------------------
# Project root on sys.path so Core imports resolve
# ----------------------------------------------------------------------
REPO_ROOT = Path(r"C:\VS Code\Alpaca-Bot")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ----------------------------------------------------------------------
# Standard library imports
# ----------------------------------------------------------------------
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Third‑party / internal imports
# ----------------------------------------------------------------------
from dotenv import load_dotenv

# Core components
from Core.Setups.container import load_config_from_env, Container

# PnL Review utilities
from Core.Scripts.generate_pnl_review import generate_pnl_review
from Core.Contexts.Reviews.review_schema import PnLReview

# ----------------------------------------------------------------------
# Helper: Load and validate recent PnL reviews (JSON files)
# ----------------------------------------------------------------------
def load_recent_pnl_reviews(limit: int = 5):
    """
    Load the most recent PnL review JSON files from Core/Contexts/Reviews,
    validate them against the PnLReview schema, and return a list of dicts.
    """
    review_dir = REPO_ROOT / "Core" / "Contexts" / "Reviews"
    if not review_dir.is_dir():
        logger.warning("PnL review directory not found: %s", review_dir)
        return []

    # Grab JSON files sorted by modification time (newest first)
    json_files = sorted(review_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    recent_files = json_files[:limit]

    validated_reviews = []
    for f in recent_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)

            # Validate with PnLReview; if validation fails we skip the review
            review = PnLReview(**data)
            validated_reviews.append(review.model_dump())
        except Exception as e:
            logger.warning("Failed to validate review %s: %s", f, e)

    return validated_reviews


# ----------------------------------------------------------------------
# Main orchestration function
# ----------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Integrated Worker-Critic with Alpaca Tool Registration")
    print("=" * 60)

    try:
        # --------------------------------------------------------------
        # 1. Load configuration (environment variables)
        # --------------------------------------------------------------
        print("\n1. Loading configuration...")
        config = load_config_from_env()

        # Validate required Alpaca credentials
        if not config.get("ALPACA_API_KEY") or not config.get("ALPACA_SECRET_KEY"):
            raise ValueError("Alpaca API credentials not found in environment variables")

        print("   ✓ Configuration loaded successfully")

        # --------------------------------------------------------------
        # 2. Create DI container
        # --------------------------------------------------------------
        print("\n2. Creating dependency injection container...")
        container = Container(config)

        # --------------------------------------------------------------
        # 3. Initialize key components
        # --------------------------------------------------------------
        print("\n3. Initializing components...")
        broker = container.get_alpaca_broker()
        if not broker.connect():
            raise ConnectionError("Failed to connect to Alpaca Paper Trading API")
        account_info = broker.get_account_info()
        print(f"   ✓ Connected to Alpaca Paper Trading")
        print(f"   Account: #{account_info.get('account_number')}")
        print(f"   Cash Balance: ${account_info.get('cash_balance', 0):,.2f}")
        print(f"   Total Equity: ${account_info.get('total_equity', 0):,.2f}")

        llm_client = container.get_ollama_client()
        models = llm_client.get_available_models()
        print(f"   ✓ Ollama connected at {llm_client.base_url}")
        print(f"   Available models: {', '.join(models) if models else 'None'}")

        vector_store = container.get_vector_store()
        print("   ✓ Vector store initialized")

        worker = container.get_generator_worker()
        print(f"   ✓ Generator Worker initialized (Model: {worker.worker_model})")
        print(f"   Tickers: {worker.tickers}")

        critic = container.get_critic_auditor()
        print("   ✓ Critic Auditor initialized")

        risk_manager = container.get_risk_manager()
        print("   ✓ Risk Manager initialized")

        # --------------------------------------------------------------
        # 4. Tool Registry (28+ tools)
        # --------------------------------------------------------------
        print("\n4. Getting Tool Registry...")
        tool_registry = container.get_tool_registry()
        tools = tool_registry.list_tools()
        print(f"   ✓ Tool registry ready with {len(tools)} tools")

        # Group tools by category for display
        categories = {}
        for tool in tools:
            cat = tool["category"]
            categories.setdefault(cat, []).append(tool)

        print("\n10. Tool Summary:")
        for category, tool_list in categories.items():
            print(f"   {category.upper()} TOOLS ({len(tool_list)}):")
            for tool in tool_list:
                print(f"     - {tool['name']}: {tool['description']}")

        # --------------------------------------------------------------
        # 5. Demonstrate key tools
        # --------------------------------------------------------------
        print("\n11. Demonstrating key tools...")

        # Account info via tool
        result = tool_registry.execute_tool("alpaca.get_account_info")
        if result["status"] == "success":
            acc = result["result"]
            print(f"   ✓ Alpaca Account Info: Cash=${acc.get('cash_balance', 0):,.2f}, Equity=${acc.get('total_equity', 0):,.2f}")

        # Latest NVDA quote
        result = tool_registry.execute_tool("alpaca.get_latest_quote", "NVDA")
        if result["status"] == "success":
            quote = result["result"]
            print(f"   ✓ NVDA Quote: Bid=${quote.get('bid_price', 0):.2f}, Ask=${quote.get('ask_price', 0):.2f}")

        # Market data for NVDA (worker tool)
        result = tool_registry.execute_tool("worker.fetch_market_data", "NVDA", limit=5)
        if result["status"] == "success":
            print(f"   ✓ Market Data: Retrieved {result['result'].get('count', 0)} data points for NVDA")

        # Generate a signal (Worker) - now using researcher persona
        result = tool_registry.execute_tool("worker.generate_signal", "NVDA")
        if result["status"] == "success" and result["result"]:
            signal = result["result"]
            print(f"   ✓ Generated Signal: {signal.action} {signal.quantity} NVDA @ ${signal.target_price:.2f} (Conf: {signal.confidence:.2f})")
            # --------------------------------------------------------------
            # 6. Integrate PnL Review processing (moved up)
            # --------------------------------------------------------------
            print("\n12. PnL Review processing...")
            recent_reviews = load_recent_pnl_reviews(limit=3)
            if recent_reviews:
                print(f"   ✓ Loaded {len(recent_reviews)} recent PnL reviews")
                # Feed each review into the critic for learning
                for i, rev in enumerate(recent_reviews, 1):
                    print(f"     [{i}] review_id={rev['review_id']}  ticker={rev['ticker']}  pnl={rev['realized_pnl']}")
                    critic.receive_pnl_review(rev)
            else:
                print("   ℹ No PnL reviews found to process")
                # Example hook: critic.receive_pnl_review(rev)  <-- future extension

            # Get current price for critic audit
            quote_result = tool_registry.execute_tool("alpaca.get_latest_quote", "NVDA")
            if quote_result["status"] == "success" and quote_result["result"]:
                quote = quote_result["result"]
                current_price = (quote.get('ask_price', 0) + quote.get('bid_price', 0)) / 2
                if current_price == 0:
                    # fallback to last price or something
                    current_price = quote.get('ask_price', quote.get('bid_price', 0))
            else:
                current_price = signal.target_price  # fallback

            # Critic audits the signal with loaded reviews
            audit_result = critic.audit_proposed_signal(signal, current_price)
            if audit_result["status"] == "success":
                print(f"   ✓ Critic audit: {audit_result.get('reason')}")
                if not audit_result["approved"]:
                    print("   ℹ Signal rejected by critic")
                    signal = None
            else:
                print(f"   ⚠ Critic audit failed: {audit_result.get('error')}")
                signal = None
        else:
            print("   ℹ No signal generated (holding)")

        # --------------------------------------------------------------
        # 8. Final summary
        # --------------------------------------------------------------
        print("\n" + "=" * 60)
        print("INTEGRATION COMPLETE")
        print("All Worker-Critic components and Alpaca tools are registered and ready.")
        print("Use tool_registry.execute_tool('tool_name', *args) to invoke any tool.")
        print("=" * 60)

        # Return objects for external inspection (e.g., UI)
        return {
            "broker": broker,
            "worker": worker,
            "critic": critic,
            "risk_manager": risk_manager,
            "tool_registry": tool_registry,
            "llm_client": llm_client,
            "vector_store": vector_store,
            "container": container,
        }

    except Exception as e:
        print(f"\n❌ Error during integration: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()