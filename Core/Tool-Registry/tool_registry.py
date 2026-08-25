#!/usr/bin/env python3
"""
Tool Registry for registering and managing all available tools.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self, broker, worker, critic, risk_manager, vector_store, llm_client):
        self.broker = broker
        self.worker = worker
        self.critic = critic
        self.risk_manager = risk_manager
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.tools = {}
        self._register_all_tools()

    def _register_all_tools(self):
        self._register_alpaca_tools()
        self._register_worker_tools()
        self._register_critic_tools()
        self._register_risk_manager_tools()
        self._register_utility_tools()

    def _register_alpaca_tools(self):
        alpaca_tools = {
            'get_account_info': self.broker.get_account_info,
            'get_positions': self.broker.get_positions,
            'get_latest_quote': self.broker.get_latest_quote,
            'scan_shark_activity': self.broker.scan_shark_activity,
            'get_market_data': self.broker.get_market_data,
            'place_order': self._place_order_wrapper,
            'cancel_order': self.broker.cancel_order,
            'get_order_status': self.broker.get_order_status
        }
        for name, func in alpaca_tools.items():
            self.tools[f'alpaca.{name}'] = {
                'function': func,
                'description': self._get_alpaca_tool_description(name),
                'category': 'alpaca'
            }

    def _register_worker_tools(self):
        worker_tools = {
            'fetch_market_data': self.worker.fetch_market_data,
            'calculate_technical_indicator': self.worker.calculate_technical_indicator,
            'execute_order': self.worker.execute_order,
            'get_portfolio': self.worker.get_portfolio,
            'check_trade_risk': self.worker.check_trade_risk,
            'generate_signal': self.worker.generate_signal
        }
        for name, func in worker_tools.items():
            self.tools[f'worker.{name}'] = {
                'function': func,
                'description': self._get_worker_tool_description(name),
                'category': 'worker'
            }

    def _register_critic_tools(self):
        critic_tools = {
            'analyze_market_psychology': self.critic.analyze_market_psychology,
            'audit_proposed_signal': self.critic.audit_proposed_signal,
            'detect_market_regime': self.critic.detect_market_regime,
            'analyze_risk_scenarios': self.critic.analyze_risk_scenarios,
            'validate_trade_signal': self.critic.validate_trade_signal,
            'query_knowledge_base': self.critic.query_knowledge_base,
            'conduct_post_mortem_autopsy': self.critic.conduct_post_mortem_autopsy
        }
        for name, func in critic_tools.items():
            self.tools[f'critic.{name}'] = {
                'function': func,
                'description': self._get_critic_tool_description(name),
                'category': 'critic'
            }

    def _register_risk_manager_tools(self):
        risk_manager_tools = {
            'check_trade_signal': self.risk_manager.check_trade_signal,
            'assess_risk_with_llm': self.risk_manager.assess_risk_with_llm
        }
        for name, func in risk_manager_tools.items():
            self.tools[f'risk.{name}'] = {
                'function': func,
                'description': self._get_risk_manager_tool_description(name),
                'category': 'risk'
            }

    def _register_utility_tools(self):
        utility_tools = {
            'load_persona': self.llm_client.load_persona,
            'load_manifest': self.llm_client.load_manifest,
            'chat_with_ollama': self.llm_client.chat,
            'vector_store_query': self.vector_store.query_knowledge,
            'vector_store_add_text': self.vector_store.add_text
        }
        for name, func in utility_tools.items():
            self.tools[f'utility.{name}'] = {
                'function': func,
                'description': self._get_utility_tool_description(name),
                'category': 'utility'
            }

    def _get_alpaca_tool_description(self, tool_name):
        descriptions = {
            'get_account_info': 'Fetch real account balances, cash, buying power, and portfolio value from Alpaca.',
            'get_positions': 'Fetch open positions from Alpaca.',
            'get_latest_quote': 'Get the latest Level 1 Top of Book quote (Bid, Ask, Bid Size, Ask Size).',
            'scan_shark_activity': 'Detect institutional footprints: whale block trades, aggressor order flow, cumulative volume delta (CVD), liquidity sweeps.',
            'get_market_data': 'Get OHLCV historical candlestick bars from Alpaca Market Data v2.',
            'place_order': 'Place a real paper order with Alpaca Markets API.',
            'cancel_order': 'Cancel an open order on Alpaca.',
            'get_order_status': 'Fetch current order status by Alpaca order ID.'
        }
        return descriptions.get(tool_name, f'Alpaca tool: {tool_name}')

    def _get_worker_tool_description(self, tool_name):
        descriptions = {
            'fetch_market_data': 'Fetch market data for a given ticker.',
            'calculate_technical_indicator': 'Calculate a technical indicator for a given ticker.',
            'execute_order': 'Execute a buy or sell order in the paper trading sandbox.',
            'get_portfolio': 'Retrieve current portfolio state including cash, positions, and P&L.',
            'check_trade_risk': 'Validate a proposed trade against risk invariants.',
            'generate_signal': 'Generate a trade signal using the Researcher Persona.'
        }
        return descriptions.get(tool_name, f'Worker tool: {tool_name}')

    def _get_critic_tool_description(self, tool_name):
        descriptions = {
            'analyze_market_psychology': 'Analyze market sentiment, fear/greed indices, and behavioral patterns using DeepSeek-R1 and ChromaDB.',
            'audit_proposed_signal': 'Deep Chain-of-Thought risk audit of a proposed trade signal from Worker Agent.',
            'detect_market_regime': 'Identify the current macro market regime based on key indicators.',
            'analyze_risk_scenarios': 'Performs stress testing and scenario analysis on a proposed trade or portfolio.',
            'validate_trade_signal': 'Validates an executed trade against the original signal and checks for slippage, fees, and adherence.',
            'query_knowledge_base': 'Queries the embedded ChromaDB vector store for relevant market psychology, regime indicators, or historical cases.',
            'conduct_post_mortem_autopsy': 'Conduct a DeepSeek-R1 Post-Mortem Autopsy on a losing or stopped-out trade.'
        }
        return descriptions.get(tool_name, f'Critic tool: {tool_name}')

    def _get_risk_manager_tool_description(self, tool_name):
        descriptions = {
            'check_trade_signal': 'Check a trade signal against the trading rules (stop-loss, take-profit, position sizing, risk-reward ratio, shark activity, etc.).',
            'assess_risk_with_llm': 'Use the LLM with the finance-investment-researcher persona to provide a detailed risk assessment of a trade signal.'
        }
        return descriptions.get(tool_name, f'Risk tool: {tool_name}')

    def _get_utility_tool_description(self, tool_name):
        descriptions = {
            'load_persona': 'Load a persona markdown file for LLM prompting.',
            'load_manifest': 'Load a tool manifest markdown file for LLM prompting.',
            'chat_with_ollama': 'Send a chat message to the Ollama LLM.',
            'vector_store_query': 'Query the vector store for similar vectors using query_knowledge method.',
            'vector_store_add_text': 'Add a text document to the vector store.'
        }
        return descriptions.get(tool_name, f'Utility tool: {tool_name}')

    def _place_order_wrapper(self, order):
        # Import here to avoid circular import
        from Core.Alpaca.alpaca_broker import OrderContract
        if not isinstance(order, OrderContract):
            # If it's a dict, convert to OrderContract (for backward compatibility)
            # In a real implementation, we might want to handle this differently
            raise ValueError("Expected OrderContract object")
        return self.broker.place_order(order)

    def get_tool(self, name):
        return self.tools.get(name)

    def list_tools(self):
        return [{
            'name': name,
            'description': tool['description'],
            'category': tool['category']
        } for name, tool in self.tools.items()]

    def execute_tool(self, name, *args, **kwargs):
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry.")
        try:
            result = tool['function'](*args, **kwargs)
            return {
                'status': 'success',
                'tool': name,
                'result': result
            }
        except Exception as e:
            return {
                'status': 'error',
                'tool': name,
                'error': str(e)
            }