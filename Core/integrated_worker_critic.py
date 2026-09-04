#!/usr/bin/env python3
"""
Integrated Worker-Critic Orchestration Script
Main script for the integrated Worker-Critic system with Alpaca tool registration.
This script uses the DAG-based orchestrator to execute the trading pipeline.
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

# DAG Orchestrator
from Core.Orchestration.dag_orchestrator import create_default_dag

def main():
    print("=" * 60)
    print("Integrated Worker-Critic with Alpaca Tool Registration (DAG Orchestrator)")
    print("=" * 60)

    try:
        # Create and run the DAG orchestrator
        print("\n1. Creating DAG orchestrator...")
        orchestrator = create_default_dag()
        print("   ✓ DAG orchestrator created successfully")
        
        print("\n2. Running DAG orchestrator...")
        final_context = orchestrator.run()
        print("   ✓ DAG orchestrator completed successfully")
        
        # Extract components from the final context for backward compatibility
        # and external inspection (e.g., UI)
        broker = final_context.get("broker")
        worker = final_context.get("worker")
        critic = final_context.get("critic")
        risk_manager = final_context.get("risk_manager")
        tool_registry = final_context.get("tool_registry")
        llm_client = final_context.get("llm_client")
        container = final_context.get("container")
        
        # Print final summary
        print("\n" + "=" * 60)
        print("INTEGRATION COMPLETE")
        print("All Worker-Critic components and Alpaca tools are registered and ready.")
        print("Use tool_registry.execute_tool('tool_name', *args) to invoke any tool.")
        print("=" * 60)
        
        # Log key information from the context
        if broker and hasattr(broker, 'get_account_info'):
            try:
                account_info = broker.get_account_info()
                print(f"   Account: #{account_info.get('account_number')}")
                print(f"   Cash Balance: ${account_info.get('cash_balance', 0):,.2f}")
                print(f"   Total Equity: ${account_info.get('total_equity', 0):,.2f}")
            except Exception as e:
                logger.warning(f"Could not get account info: {e}")
        
        if tool_registry:
            tools = tool_registry.list_tools()
            print(f"   Tool registry ready with {len(tools)} tools")
            
        # Return objects for external inspection (e.g., UI)
        return {
            "broker": broker,
            "worker": worker,
            "critic": critic,
            "risk_manager": risk_manager,
            "tool_registry": tool_registry,
            "llm_client": llm_client,
            "container": container,
            "orchestrator": orchestrator,  # Also return the orchestrator for inspection
            "final_context": final_context,  # And the full context
        }

    except Exception as e:
        print(f"\n❌ Error during integration: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()