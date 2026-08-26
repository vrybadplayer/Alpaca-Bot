# ADR 002 - DAG-Based Orchestrator, PnL Review, and Risk Review

## Context
The Alpaca-Bot trading system has evolved to include multiple components: Worker (signal generation), Critic (audit and learning), Risk Manager (rule-based and LLM-based assessment), and the Alpaca broker for order execution. Additionally, the system persists Post-trade PnL (Profit and Loss) reviews as JSON files for continuous learning.

Initially, the orchestration of these components was handled in a procedural manner in `core/integrated_worker_critic.py`. This approach made it difficult to:
- Clearly see the dependencies between steps.
- Modify or extend the pipeline without changing the core logic.
- Run independent steps in parallel (e.g., loading PnL reviews and fetching market data).
- Ensure that the critic's learned context (from PnL reviews) is always available before auditing a signal, especially after a system reboot.

## Decision
We introduce a Directed Acyclic Graph (DAG) based orchestrator to manage the trading pipeline. The orchestrator defines each step as a node with explicit inputs and outputs, and edges represent dependencies. This provides:
- A clear, visualizable workflow.
- Guaranteed execution order respecting dependencies.
- Ability to run independent nodes in parallel (though the current implementation runs sequentially for simplicity, the DAG structure allows for future parallel execution).
- Improved testability and maintainability.

Additionally, we formalize the handling of PnL reviews and risk reviews:

### PnL Review Handling
- PnL reviews are stored as JSON files in `Core/Contexts/Reviews/`.
- Each review is validated against a Pydantic `PnLReview` model (using Pydantic v2's `model_dump`).
- The Critic component exposes two methods:
  - `store_review(review)`: Persists a validated review to disk.
  - `receive_pnl_review(review)`: Loads a review into the Critic's internal knowledge base (for use in auditing).
- In the pipeline, PnL reviews are loaded from disk (most recent first) and fed into the critic via `receive_pnl_review` **before** the critic audits a worker-generated signal. This ensures the critic's audit is informed by historical trade outcomes.

### Risk Review Handling
- Risk assessment consists of two parts:
  1. Rule-based checking (e.g., stop-loss, take-profit, position sizing, risk-reward ratio) performed by the `RiskManager`.
  2. LLM-based assessment using the `finance-investment-researcher` persona for a deeper analysis of the trade signal.
- The risk check node in the DAG runs after the critic audit and before order placement. It uses the `worker.check_trade_risk` tool (which internally uses the risk manager) to validate the signal against trading rules.
- If the risk check fails, the signal is rejected and no order is placed.

## Consequences
- **Improved Modularity**: Each step (loading config, initializing components, generating signal, loading PnL feeds, critic audit, risk check, order placement) is a separate node, making it easier to modify or replace individual steps.
- **Explicit Dependencies**: The DAG makes it clear that the critic audit depends on both the worker signal and the loaded PnL reviews, and that the risk check depends on the critic's approval.
- **Extensibility**: New steps (e.g., additional validation, alternative data sources) can be added as new nodes with appropriate edges.
- **Robustness**: The orchestrator includes error handling and logging for each node, and the DAG structure prevents steps from running out of order.
- **No Breaking Changes**: The existing functionality of the Worker-Critic system is preserved; the orchestrator simply re-organizes the execution flow.

## Implementation Details
- The DAG orchestrator is implemented in `Core/Orchestration/dag_orchestrator.py`.
- The main entry point remains `core/integrated_worker_critic.py`, which now simply creates and runs the DAG orchestrator (though for now we keep the original script for backward compatibility and testing; the orchestrator can be run independently).
- The orchestrator uses a topological sort (Kahn's algorithm) to determine the execution order.
- Each node function receives a context dictionary (containing the outputs of its predecessor nodes) and returns a dictionary of updates to be merged into the context.

## Related Files
- `Core/Orchestration/dag_orchestrator.py` - The DAG orchestrator implementation.
- `Core/Worker_Critic/critic.py` - Updated to include `store_review` and `receive_pnl_review` methods.
- `Core/Contexts/Reviews/review_schema.py` - Pydantic model for PnL review validation.
- `Core/Contexts/Reviews/` - Directory storing JSON PnL review files.
- `Core/Risk/risk_manager.py` - Rule-based risk checking.
- `Core/Tool_Registry/utils.py` - Shared utilities (OrderContract, enums, etc.).