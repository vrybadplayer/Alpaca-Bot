# ADR 001 - Enterprise Folder Structure

## Context
The Alpaca-Bot project has grown to include many components including:
- Alpaca broker implementation
- Worker and Critic agents
- Risk management system
- LLM integration for persona-based analysis
- Tool registry with 28+ tools

Initially, files were scattered across the repository, making it difficult to locate components and understand their relationships.

## Decision
Organize the codebase into a structured hierarchy under `Core/` with well-defined subdirectories:
- `Core/Alpaca/` - Alpaca broker implementation
- `Core/Setups/` - Configuration, container, and Ollama client setup  
- `Core/Tool_Registry/` - Tool registry and utilities
- `Core/Worker_Critic/` - Worker and Critic implementations
- `Core/Risk/` - Risk manager implementation
- `Personas/` - All persona markdown files
- `Contexts/` - Hermes contexts including new `ADR/` and `Reviews/` subfolders
- `Additions/examples/` - Moved example Alpaca API scripts

This structure follows Python packaging best practices and improves navigability, testability, and maintainability.

## Consequences
- Improved code organization and discoverability
- Clear separation of concerns
- Easier onboarding for new contributors
- Better alignment with enterprise codebase standards
- No breaking changes to functionality