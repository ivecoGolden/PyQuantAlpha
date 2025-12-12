# src/ai/__init__.py
"""AI 策略生成模块"""

from .base import BaseLLMClient, ChatResult, STRATEGY_KEYWORDS
from .deepseek import DeepSeekClient
from .factory import LLMProvider, create_llm_client
from .prompt import SYSTEM_PROMPT, ADVANCED_PROMPT, CHAT_SYSTEM_PROMPT
from .validator import validate_strategy_code, execute_strategy_code

__all__ = [
    "BaseLLMClient",
    "ChatResult",
    "STRATEGY_KEYWORDS",
    "DeepSeekClient",
    "LLMProvider",
    "create_llm_client",
    "SYSTEM_PROMPT",
    "ADVANCED_PROMPT",
    "CHAT_SYSTEM_PROMPT",
    "validate_strategy_code",
    "execute_strategy_code",
]

