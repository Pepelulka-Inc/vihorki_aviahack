"""
UX Metrics Analysis Service

This service provides two main clients:
1. API Client - handles metrics API according to OpenAPI contract
2. LLM Client - communicates with Yandex Cloud AI for analysis

Refactored structure:
- clients/ - API and LLM clients
- constants/ - System prompts and templates
- utils/ - Helper functions (prompt formatting)
- models.py - Pydantic data models
- orchestrator.py - Main workflow coordinator
- config.py - Configuration management
"""

from .clients import APIClient, LLMClient
from .orchestrator import AnalysisOrchestrator
from .models import MetricsPayload
from .config import load_config

__all__ = [
    'APIClient',
    'LLMClient',
    'AnalysisOrchestrator',
    'MetricsPayload',
    'load_config',
]

__version__ = '1.0.0'