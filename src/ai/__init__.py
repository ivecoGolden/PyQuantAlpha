# src/ai/__init__.py
"""AI 策略生成模块"""

from .base import BaseLLMClient, ChatResult, LLMResponse
from .deepseek import DeepSeekClient
from .factory import LLMProvider, create_llm_client
from .prompt import SYSTEM_PROMPT
from src.backtest.loader import validate_strategy_code, execute_strategy_code

__all__ = [
    "BaseLLMClient",
    "ChatResult",
    "LLMResponse",
    "DeepSeekClient",
    "LLMProvider",
    "create_llm_client",
    "SYSTEM_PROMPT",
    "validate_strategy_code",
    "execute_strategy_code",
]
