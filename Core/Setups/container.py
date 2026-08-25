#!/usr/bin/env python3
"""
Dependency Injection Container for the Worker-Critic system.
Manages the creation and wiring of all components.
"""

import os
from typing import Dict, Any

from Core.Alpaca.alpaca_broker import AlpacaBroker
from Core.Setups.ollama_client import OllamaClient
from Core.utils import VectorStore
from Core.worker import GeneratorWorker
from Core.critic import CriticAuditor
from Core.Risk.risk_manager import RiskManager
from Core.tool_registry import ToolRegistry


class Container:
    """Dependency injection container."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._singletons = {}
    
    def get_alpaca_config(self) -> Dict[str, Any]:
        """Get Alpaca-specific configuration."""
        return {
            'api_key': self.config.get('ALPACA_API_KEY') or self.config.get('APCA_API_KEY_ID'),
            'api_secret': self.config.get('ALPACA_SECRET_KEY') or self.config.get('APCA_API_SECRET_KEY'),
            'base_url': 'https://paper-api.alpaca.markets',
            'data_url': 'https://data.alpaca.markets',
            'data_feed': 'iex',
            'paper_trading': True,
            'live_enabled': False,
            'sandbox_initial_balance': 100000.0,
            'shark_block_threshold_usd': 150000.0,
            'shark_block_min_shares': 1000,
            'commission_per_trade': 0.0,
            'slippage_model': 'fixed'
        }
    
    def get_worker_config(self) -> Dict[str, Any]:
        """Get Worker-specific configuration."""
        alpaca_config = self.get_alpaca_config()
        ollama_url = self.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        return {
            'tickers': ['NVDA'],
            'timeframe': '1D',
            'lookback_period': 20,
            'broker': alpaca_config,
            'system': {
                'cash_reserve': 5000.0
            },
            'model_routing': {
                'ollama_base_url': ollama_url,
                'worker_engine': {
                    'primary': 'qwen2.5-coder:7b',
                    'temperature': 0.1
                },
                'risk_manager_engine': {
                    'primary': 'qwen2.5-coder:7b',
                    'temperature': 0.1
                }
            }
        }
    
    def get_alpaca_broker(self) -> AlpacaBroker:
        """Get Alpaca broker instance (singleton)."""
        if 'alpaca_broker' not in self._singletons:
            alpaca_config = self.get_alpaca_config()
            self._singletons['alpaca_broker'] = AlpacaBroker(alpaca_config)
        return self._singletons['alpaca_broker']
    
    def get_ollama_client(self) -> OllamaClient:
        """Get Ollama client instance (singleton)."""
        if 'ollama_client' not in self._singletons:
            ollama_url = self.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
            personas_dir = os.path.join(os.path.dirname(__file__), 'personas')
            manifests_dir = os.path.join(os.path.dirname(__file__), 'manifests')
            self._singletons['ollama_client'] = OllamaClient(
                base_url=ollama_url,
                personas_dir=personas_dir,
                manifests_dir=manifests_dir
            )
        return self._singletons['ollama_client']
    
    def get_vector_store(self) -> VectorStore:
        """Get Vector store instance (singleton)."""
        if 'vector_store' not in self._singletons:
            self._singletons['vector_store'] = VectorStore()
        return self._singletons['vector_store']
    
    def get_generator_worker(self) -> GeneratorWorker:
        """Get Generator Worker instance (singleton)."""
        if 'generator_worker' not in self._singletons:
            worker_config = self.get_worker_config()
            alpaca_broker = self.get_alpaca_broker()
            ollama_client = self.get_ollama_client()
            vector_store = self.get_vector_store()
            
            self._singletons['generator_worker'] = GeneratorWorker({
                'broker': worker_config['broker'],
                'system': worker_config['system'],
                'model_routing': worker_config['model_routing'],
                'tickers': worker_config['tickers'],
                'timeframe': worker_config['timeframe'],
                'lookback_period': worker_config['lookback_period']
            })
            # Manually set the dependencies that GeneratorWorker expects
            worker = self._singletons['generator_worker']
            worker.broker = alpaca_broker
            worker.vector_store = vector_store
            worker.llm_client = ollama_client
        return self._singletons['generator_worker']
    
    def get_critic_auditor(self) -> CriticAuditor:
        """Get Critic Auditor instance (singleton)."""
        if 'critic_auditor' not in self._singletons:
            worker_config = self.get_worker_config()
            alpaca_broker = self.get_alpaca_broker()
            ollama_client = self.get_ollama_client()
            vector_store = self.get_vector_store()
            
            self._singletons['critic_auditor'] = CriticAuditor({
                'broker': worker_config['broker'],
                'system': worker_config['system'],
                'model_routing': worker_config['model_routing'],
                'tickers': worker_config['tickers'],
                'lookback_days': worker_config.get('lookback_days', 30)
            })
            # Manually set the dependencies that CriticAuditor expects
            critic = self._singletons['critic_auditor']
            critic.broker = alpaca_broker
            critic.vector_store = vector_store
            critic.llm_client = ollama_client
        return self._singletons['critic_auditor']
    
    def get_risk_manager(self) -> RiskManager:
        """Get Risk Manager instance (singleton)."""
        if 'risk_manager' not in self._singletons:
            worker_config = self.get_worker_config()
            alpaca_broker = self.get_alpaca_broker()
            ollama_client = self.get_ollama_client()
            vector_store = self.get_vector_store()
            
            self._singletons['risk_manager'] = RiskManager({
                'broker': worker_config['broker'],
                'system': worker_config['system'],
                'model_routing': worker_config['model_routing'],
                'tickers': worker_config['tickers'],
                'lookback_days': worker_config.get('lookback_days', 30)
            })
            # Manually set the dependencies that RiskManager expects
            risk_manager = self._singletons['risk_manager']
            risk_manager.broker = alpaca_broker
            risk_manager.vector_store = vector_store
            risk_manager.llm_client = ollama_client
        return self._singletons['risk_manager']
    
    def get_tool_registry(self) -> ToolRegistry:
        """Get Tool Registry instance (singleton)."""
        if 'tool_registry' not in self._singletons:
            alpaca_broker = self.get_alpaca_broker()
            worker = self.get_generator_worker()
            critic = self.get_critic_auditor()
            risk_manager = self.get_risk_manager()
            vector_store = self.get_vector_store()
            ollama_client = self.get_ollama_client()
            
            self._singletons['tool_registry'] = ToolRegistry(
                broker=alpaca_broker,
                worker=worker,
                critic=critic,
                risk_manager=risk_manager,
                vector_store=vector_store,
                llm_client=ollama_client
            )
        return self._singletons['tool_registry']


def load_config_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    from dotenv import load_dotenv
    import os
    
    # Load .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=env_path)
    
    # Return all relevant environment variables as config
    return {
        'ALPACA_API_KEY': os.getenv('ALPACA_API_KEY'),
        'ALPACA_SECRET_KEY': os.getenv('ALPACA_SECRET_KEY'),
        'OLLAMA_BASE_URL': os.getenv('OLLAMA_BASE_URL'),
        # Add any other config vars as needed
    }