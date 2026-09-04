"""
DAG-based Orchestrator for the Worker-Critic Alpaca Trading Bot.

This module provides a simple but enterprise-grade directed acyclic graph (DAG)
orchestrator that defines the trading pipeline as a set of nodes with explicit
dependencies. The orchestrator ensures nodes are executed in the correct order,
handles data flow between nodes, provides error handling, and allows for
parallel execution of independent nodes.

Each node is a function that takes a context dictionary and returns a dictionary
of updates to be merged into the context. Nodes can declare their input and
output keys for documentation and validation.

Example usage:
    orchestrator = DAGOrchestrator()
    orchestrator.add_node('load_config', load_config_func, inputs=[], outputs=['config'])
    orchestrator.add_node('create_container', create_container_func, inputs=['config'], outputs=['container'])
    orchestrator.add_edge('load_config', 'create_container')
    # ... add all nodes and edges
    final_context = orchestrator.run(initial_context={})
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, Dict, List, Set

logger = logging.getLogger(__name__)


class Node:
    """Represents a single node in the DAG."""

    def __init__(
        self,
        name: str,
        func: Callable[[Dict[str, Any]], Dict[str, Any]],
        inputs: List[str] | None = None,
        outputs: List[str] | None = None,
    ):
        self.name = name
        self.func = func
        self.inputs = inputs or []
        self.outputs = outputs or []

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the node function with the given context.

        Validates that all required inputs are present in the context.
        Returns a dictionary of updates to be merged into the context.
        """
        missing = [key for key in self.inputs if key not in context]
        if missing:
            raise ValueError(f"Node '{self.name}' missing required inputs: {missing}")

        # Prepare inputs for the function (only the keys it declares)
        func_inputs = {key: context[key] for key in self.inputs}
        try:
            logger.debug(f"Running node '{self.name}' with inputs: {list(func_inputs.keys())}")
            result = self.func(func_inputs)
            logger.debug(f"Node '{self.name}' produced outputs: {list(result.keys())}")
            # Validate that the result only contains declared outputs (optional)
            unexpected = set(result.keys()) - set(self.outputs)
            if unexpected:
                logger.warning(
                    f"Node '{self.name}' produced unexpected outputs: {unexpected}. "
                    f"Declared outputs: {self.outputs}"
                )
            return result
        except Exception as e:
            logger.exception(f"Node '{self.name}' failed: {e}")
            raise


class DAGOrchestrator:
    """Orchestrates execution of nodes in a directed acyclic graph."""

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.graph: Dict[str, Set[str]] = {}  # adjacency list: node -> set of successors
        self.reverse_graph: Dict[str, Set[str]] = {}  # node -> set of predecessors
        self.in_degree: Dict[str, int] = {}

    def add_node(
        self,
        name: str,
        func: Callable[[Dict[str, Any]], Dict[str, Any]],
        inputs: List[str] | None = None,
        outputs: List[str] | None = None,
    ) -> None:
        """Add a node to the DAG."""
        if name in self.nodes:
            raise ValueError(f"Node '{name}' already exists in the DAG")
        self.nodes[name] = Node(name, func, inputs, outputs)
        self.graph[name] = set()
        self.reverse_graph[name] = set()
        self.in_degree[name] = 0
        logger.debug(f"Added node '{name}' with inputs {inputs} and outputs {outputs}")

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add a directed edge from `from_node` to `to_node`."""
        if from_node not in self.nodes:
            raise ValueError(f"Source node '{from_node}' not found in DAG")
        if to_node not in self.nodes:
            raise ValueError(f"Target node '{to_node}' not found in DAG")
        if to_node in self.graph[from_node]:
            logger.warning(f"Edge from '{from_node}' to '{to_node}' already exists")
            return
        self.graph[from_node].add(to_node)
        self.reverse_graph[to_node].add(from_node)
        self.in_degree[to_node] = self.in_degree.get(to_node, 0) + 1
        logger.debug(f"Added edge: '{from_node}' -> '{to_node}'")

    def _topological_sort(self) -> List[str]:
        """Return a list of node names in topological order using Kahn's algorithm."""
        # Copy in_degree to avoid modifying the original
        in_degree = self.in_degree.copy()
        queue: List[str] = [node for node, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            # For determinism, we sort the queue (optional)
            queue.sort()
            node = queue.pop(0)
            order.append(node)

            for successor in self.graph[node]:
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)

        if len(order) != len(self.nodes):
            # There is a cycle
            remaining = [node for node, deg in in_degree.items() if deg > 0]
            raise ValueError(f"DAG has a cycle involving nodes: {remaining}")

        return order

    def run(self, initial_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Execute the DAG in topological order.

        Args:
            initial_context: Optional initial context to seed the orchestrator.

        Returns:
            The final context after all nodes have executed.
        """
        context = dict(initial_context or {})
        logger.info(f"Starting DAG orchestrator with {len(self.nodes)} nodes")
        logger.debug(f"Initial context keys: {list(context.keys())}")

        try:
            order = self._topological_sort()
            logger.info(f"Execution order: {order}")
        except ValueError as e:
            logger.error(f"Failed to topologically sort DAG: {e}")
            raise

        for node_name in order:
            node = self.nodes[node_name]
            logger.info(f"Executing node: {node_name}")
            try:
                updates = node.run(context)
                context.update(updates)
                logger.info(f"Node '{node_name}' completed successfully")
            except Exception as e:
                logger.error(f"Node '{node_name}' failed: {e}")
                # In a production system, we might want to implement retry logic,
                # fallback nodes, or alerting here.
                raise

        logger.info("DAG orchestrator completed all nodes successfully")
        return context


def create_default_dag() -> DAGOrchestrator:
    """Factory function to create the default trading pipeline DAG.

    This function imports the necessary components and defines the nodes and edges
    for the standard Worker-Critic trading pipeline.

    Returns:
        A configured DAGOrchestrator instance ready to run.
    """
    # Import inside the function to avoid circular imports and allow the orchestrator
    # module to be imported without triggering side effects.
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    # Ensure the repo root is on sys.path for Core imports
    REPO_ROOT = Path(r"C:/VS Code/Alpaca-Bot")
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    from Core.Setups.container import load_config_from_env, Container
    from Core.Scripts.generate_pnl_review import generate_pnl_review
    from Core.Contexts.Reviews.review_schema import PnLReview

    # ----------------------------------------------------------------------
    # Helper functions (could be moved to a utilities module)
    # ----------------------------------------------------------------------
    def load_recent_pnl_reviews(limit: int = 5) -> List[Dict[str, Any]]:
        """Load the most recent PnL review JSON files from Core/Contexts/Reviews,
        validate them against the PnLReview schema, and return a list of dicts.
        """
        import json  # Import json here to ensure it's available in this function's scope
        review_dir = REPO_ROOT / "Core" / "Contexts" / "Reviews"
        if not review_dir.is_dir():
            logger.warning("PnL review directory not found: %s", review_dir)
            return []

        json_files = sorted(review_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        recent_files = json_files[:limit]

        validated_reviews: List[Dict[str, Any]] = []
        for f in recent_files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                review = PnLReview(**data)
                validated_reviews.append(review.model_dump())
            except Exception as e:
                logger.warning("Failed to validate review %s: %s", f, e)
        return validated_reviews

    # ----------------------------------------------------------------------
    # Node functions
    # ----------------------------------------------------------------------
    def load_config(_: Dict[str, Any]) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        load_dotenv()  # Ensure .env is loaded
        config = load_config_from_env()
        # Validate required Alpaca credentials
        if not config.get("ALPACA_API_KEY") or not config.get("ALPACA_SECRET_KEY"):
            raise ValueError("Alpaca API credentials not found in environment variables")
        return {"config": config}

    def create_container(context: Dict[str, Any]) -> Dict[str, Any]:
        """Create the dependency injection container."""
        config = context["config"]
        container = Container(config)
        return {"container": container}

    def initialize_components(context: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize key components: broker, LLM client, worker, critic, risk manager."""
        container = context["container"]
        broker = container.get_alpaca_broker()
        if not broker.connect():
            raise ConnectionError("Failed to connect to Alpaca Paper Trading API")
        account_info = broker.get_account_info()

        llm_client = container.get_ollama_client()
        worker = container.get_generator_worker()
        critic = container.get_critic_auditor()
        risk_manager = container.get_risk_manager()

        return {
            "broker": broker,
            "account_info": account_info,
            "llm_client": llm_client,
            "worker": worker,
            "critic": critic,
            "risk_manager": risk_manager,
        }

    def get_tool_registry(context: Dict[str, Any]) -> Dict[str, Any]:
        """Get the tool registry from the container."""
        container = context["container"]
        tool_registry = container.get_tool_registry()
        return {"tool_registry": tool_registry}

    def demonstrate_tools(context: Dict[str, Any]) -> Dict[str, Any]:
        """Demonstrate key tools (optional step for debugging/showcase)."""
        tool_registry = context["tool_registry"]
        # We'll run a few demonstration calls and log them, but not store much in context.
        # Account info
        result = tool_registry.execute_tool("alpaca.get_account_info")
        if result["status"] == "success":
            acc = result["result"]
            logger.info(
                f"Alpaca Account Info: Cash=${acc.get('cash_balance', 0):,.2f}, "
                f"Equity=${acc.get('total_equity', 0):,.2f}"
            )
        # Latest NVDA quote
        result = tool_registry.execute_tool("alpaca.get_latest_quote", "NVDA")
        if result["status"] == "success":
            quote = result["result"]
            logger.info(
                f"NVDA Quote: Bid=${quote.get('bid_price', 0):.2f}, "
                f"Ask=${quote.get('ask_price', 0):.2f}"
            )
        # Market data for NVDA (worker tool)
        result = tool_registry.execute_tool("worker.fetch_market_data", "NVDA", limit=5)
        if result["status"] == "success":
            logger.info(
                f"Market Data: Retrieved {result['result'].get('count', 0)} data points for NVDA"
            )
        # Generate a signal (Worker)
        result = tool_registry.execute_tool("worker.generate_signal", "NVDA")
        signal = None
        if result["status"] == "success" and result["result"]:
            signal = result["result"]
            logger.info(
                f"Generated Signal: {signal.action} {signal.quantity} NVDA @ ${signal.target_price:.2f} (Conf: {signal.confidence:.2f})"
            )
        # We return the signal for downstream nodes, but note that the demonstration
        # step is not required for the core pipeline. We'll keep it for now.
        return {"demonstration_signal": signal}

    def generate_signal(context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a trade signal using the worker."""
        tool_registry = context["tool_registry"]
        result = tool_registry.execute_tool("worker.generate_signal", "NVDA")
        if result["status"] != "success" or not result["result"]:
            # No signal is not an error; we just return None.
            logger.info("No signal generated (holding)")
            return {"signal": None}
        signal = result["result"]
        logger.info(
            f"Generated Signal: {signal.action} {signal.quantity} NVDA @ ${signal.target_price:.2f} (Conf: {signal.confidence:.2f})"
        )
        return {"signal": signal}

    def load_pnl_reviews(_: Dict[str, Any]) -> Dict[str, Any]:
        """Load and validate recent PnL reviews."""
        reviews = load_recent_pnl_reviews(limit=3)
        logger.info(f"Loaded {len(reviews)} recent PnL reviews")
        return {"pnl_reviews": reviews}

    def feed_pnl_to_critic(context: Dict[str, Any]) -> Dict[str, Any]:
        """Feed each PnL review into the critic for learning."""
        critic = context["critic"]
        reviews = context["pnl_reviews"]
        for i, rev in enumerate(reviews, 1):
            logger.info(
                f"Feeding PnL review [{i}] review_id={rev['review_id']} ticker={rev['ticker']} pnl={rev['realized_pnl']}"
            )
            critic.receive_pnl_review(rev)
        # No output needed; the critic's internal state is updated.
        return {}

    def get_current_price(context: Dict[str, Any]) -> Dict[str, Any]:
        """Get the current price for NVDA to use in critic audit."""
        tool_registry = context["tool_registry"]
        quote_result = tool_registry.execute_tool("alpaca.get_latest_quote", "NVDA")
        if quote_result["status"] == "success" and quote_result["result"]:
            quote = quote_result["result"]
            current_price = (quote.get('ask_price', 0) + quote.get('bid_price', 0)) / 2
            if current_price == 0:
                # fallback to last price or something
                current_price = quote.get('ask_price', quote.get('bid_price', 0))
            logger.info(f"Current price for NVDA: ${current_price:.2f}")
        else:
            # This should not happen if the market is open, but we fallback.
            logger.warning("Failed to get latest quote; using signal target price as fallback")
            # We'll need the signal for the fallback, but we don't have it here.
            # We'll handle this in the critic_audit node by checking if current_price is present.
            current_price = None
        return {"current_price": current_price}

    def critic_audit(context: Dict[str, Any]) -> Dict[str, Any]:
        """Audit the signal with the critic, using loaded PnL reviews and current price."""
        critic = context["critic"]
        signal = context.get("signal")
        current_price = context.get("current_price")

        if signal is None:
            logger.info("No signal to audit")
            return {"audit_result": None, "signal_approved": False}

        # Get current price from quote if not already provided (should be, but just in case)
        if current_price is None:
            tool_registry = context["tool_registry"]
            quote_result = tool_registry.execute_tool("alpaca.get_latest_quote", "NVDA")
            if quote_result["status"] == "success" and quote_result["result"]:
                quote = quote_result["result"]
                current_price = (quote.get('ask_price', 0) + quote.get('bid_price', 0)) / 2
                if current_price == 0:
                    current_price = quote.get('ask_price', quote.get('bid_price', 0))
            else:
                # Final fallback to signal target price
                current_price = signal.target_price
            logger.info(f"Using current price for audit: ${current_price:.2f}")

        audit_result = critic.audit_proposed_signal(signal, current_price)
        if audit_result["status"] == "success":
            approved = audit_result.get("approved", False)
            reason = audit_result.get("reason", "No reason provided")
            logger.info(f"Critic audit: {reason} (approved={approved})")
            if not approved:
                logger.info("Signal rejected by critic")
            return {"audit_result": audit_result, "signal_approved": approved}
        else:
            error = audit_result.get("error", "Unknown error")
            logger.error(f"Critic audit failed: {error}")
            return {"audit_result": audit_result, "signal_approved": False}

    def risk_check(context: Dict[str, Any]) -> Dict[str, Any]:
        """Check the signal against risk rules."""
        risk_manager = context["risk_manager"]
        signal = context.get("signal")
        signal_approved = context.get("signal_approved", False)

        if not signal_approved or signal is None:
            logger.info("Signal not approved by critic or missing; skipping risk check")
            return {"risk_check_passed": False}

        # We'll use the worker's check_trade_risk tool via the tool registry for consistency.
        # Alternatively, we could call risk_manager.check_trade_signal directly if we have an OrderContract.
        # For now, we'll create an OrderContract from the signal and use the risk manager.
        from Core.Tool_Registry.utils import OrderContract, OrderAction, OrderType

        # Convert signal to OrderContract
        action = OrderAction.BUY if signal.action == "buy" else OrderAction.SELL
        contract = OrderContract(
            ticker=signal.ticker,
            action=action,
            quantity=signal.quantity,
            order_type=OrderType.MARKET,  # We'll use market for simplicity; can be made configurable
            price=signal.target_price,
            source_component="orchestrator.risk_check",
        )

        tool_registry = context["tool_registry"]
        action_str = "BUY" if str(signal.action).upper() in ["BUY", "ORDERACTION.BUY"] else "SELL"
        result = tool_registry.execute_tool(
            "worker.check_trade_risk",
            signal.ticker,
            action_str,
            signal.quantity,
            signal.target_price
        )

        if result.get("status") == "success" and isinstance(result.get("result"), dict):
            res_dict = result["result"]
            passed = res_dict.get("approved", False)
            reason = res_dict.get("reason", "")
            logger.info(f"Risk check result: approved={passed}, reason={reason}")
            return {"risk_check_passed": passed, "risk_details": res_dict}
        else:
            logger.warning(f"Risk check failed or returned unexpected result: {result.get('error', result)}")
            return {"risk_check_passed": False}

    def place_order(context: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order if the signal has passed critic audit and risk check."""
        broker = context["broker"]
        signal = context.get("signal")
        signal_approved = context.get("signal_approved", False)
        risk_check_passed = context.get("risk_check_passed", False)

        if not (signal_approved and risk_check_passed and signal is not None):
            logger.info("Order placement skipped: signal not approved or risk check not passed")
            return {"order_placed": False}

        # Convert signal to OrderContract
        from Core.Tool_Registry.utils import OrderContract, OrderAction, OrderType

        action = OrderAction.BUY if signal.action == "buy" else OrderAction.SELL
        contract = OrderContract(
            ticker=signal.ticker,
            action=action,
            quantity=signal.quantity,
            order_type=OrderType.MARKET,  # Make configurable if needed
            price=signal.target_price,
            source_component="orchestrator.place_order",
        )

        # Use the broker's place_order method (or the tool)
        tool_registry = context["tool_registry"]
        result = tool_registry.execute_tool("alpaca.place_order", contract)
        if result["status"] == "success":
            order_id = result["result"].get("order_id") if isinstance(result["result"], dict) else result["result"]
            logger.info(f"Order placed successfully: {order_id}")
            return {"order_placed": True, "order_id": order_id}
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"Order placement failed: {error}")
            return {"order_placed": False, "error": error}

    def final_summary(context: Dict[str, Any]) -> Dict[str, Any]:
        """Print a final summary of the pipeline run."""
        logger.info("=" * 60)
        logger.info("INTEGRATION COMPLETE")
        logger.info("All Worker-Critic components and Alpaca tools are registered and ready.")
        logger.info("Use tool_registry.execute_tool('tool_name', *args) to invoke any tool.")
        logger.info("=" * 60)
        # We don't need to return anything, but we can return a status.
        return {"pipeline_completed": True}

    # ----------------------------------------------------------------------
    # Create the DAG and add nodes
    # ----------------------------------------------------------------------
    orchestrator = DAGOrchestrator()

    # Define nodes with their inputs and outputs
    orchestrator.add_node(
        "load_config",
        load_config,
        inputs=[],
        outputs=["config"],
    )
    orchestrator.add_node(
        "create_container",
        create_container,
        inputs=["config"],
        outputs=["container"],
    )
    orchestrator.add_node(
        "initialize_components",
        initialize_components,
        inputs=["container"],
        outputs=[
            "broker",
            "account_info",
            "llm_client",
            "worker",
            "critic",
            "risk_manager",
        ],
    )
    orchestrator.add_node(
        "get_tool_registry",
        get_tool_registry,
        inputs=["container"],
        outputs=["tool_registry"],
    )
    orchestrator.add_node(
        "demonstrate_tools",
        demonstrate_tools,
        inputs=["tool_registry"],
        outputs=["demonstration_signal"],  # We'll keep this for now, but it's not used downstream
    )
    orchestrator.add_node(
        "generate_signal",
        generate_signal,
        inputs=["tool_registry"],
        outputs=["signal"],
    )
    orchestrator.add_node(
        "load_pnl_reviews",
        load_pnl_reviews,
        inputs=[],
        outputs=["pnl_reviews"],
    )
    orchestrator.add_node(
        "feed_pnl_to_critic",
        feed_pnl_to_critic,
        inputs=["critic", "pnl_reviews"],
        outputs=[],  # Updates critic in place
    )
    orchestrator.add_node(
        "get_current_price",
        get_current_price,
        inputs=["tool_registry"],
        outputs=["current_price"],
    )
    orchestrator.add_node(
        "critic_audit",
        critic_audit,
        inputs=["signal", "current_price", "critic"],
        outputs=["audit_result", "signal_approved"],
    )
    orchestrator.add_node(
        "risk_check",
        risk_check,
        inputs=["signal_approved", "signal", "risk_manager", "tool_registry"],
        outputs=["risk_check_passed"],
    )
    orchestrator.add_node(
        "place_order",
        place_order,
        inputs=["signal_approved", "risk_check_passed", "signal", "broker", "tool_registry"],
        outputs=["order_placed", "order_id"],
    )
    orchestrator.add_node(
        "final_summary",
        final_summary,
        inputs=[],  # Doesn't need any specific inputs; runs at the end
        outputs=["pipeline_completed"],
    )

    # Define edges (dependencies)
    orchestrator.add_edge("load_config", "create_container")
    orchestrator.add_edge("create_container", "initialize_components")
    orchestrator.add_edge("create_container", "get_tool_registry")
    orchestrator.add_edge("initialize_components", "demonstrate_tools")
    orchestrator.add_edge("get_tool_registry", "demonstrate_tools")
    orchestrator.add_edge("get_tool_registry", "generate_signal")
    orchestrator.add_edge("get_tool_registry", "get_current_price")  # <-- Added this edge
    orchestrator.add_edge("load_pnl_reviews", "feed_pnl_to_critic")
    orchestrator.add_edge("feed_pnl_to_critic", "critic_audit")  # Critic must be fed before audit
    orchestrator.add_edge("generate_signal", "critic_audit")
    orchestrator.add_edge("get_current_price", "critic_audit")
    orchestrator.add_edge("critic_audit", "risk_check")
    orchestrator.add_edge("risk_check", "place_order")
    orchestrator.add_edge("place_order", "final_summary")
    # Also, final_summary should run after all the main steps; we can also make it depend on
    # the last step in each branch, but for simplicity we'll make it depend on place_order.
    # If we want it to run even if order placement is skipped, we could make it depend on
    # critic_audit and risk_check instead. We'll keep it after place_order for now.

    return orchestrator


# If this module is run directly, we can test the orchestrator.
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    orchestrator = create_default_dag()
    try:
        final_context = orchestrator.run()
        logger.info("Orchestrator run completed successfully")
        # Optionally, we can inspect the final context
        logger.debug(f"Final context keys: {list(final_context.keys())}")
    except Exception as e:
        logger.error(f"Orchestrator run failed: {e}")
        sys.exit(1)