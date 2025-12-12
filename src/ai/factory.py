# src/ai/factory.py
"""LLM 客户端工厂"""

from enum import Enum

from .base import BaseLLMClient
from src.messages import ErrorMessage


class LLMProvider(Enum):
    """LLM 提供商枚举"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    CLAUDE = "claude"  # 预留


def create_llm_client(
    provider: LLMProvider,
    api_key: str,
    model: str | None = None,
    **kwargs
) -> BaseLLMClient:
    """创建 LLM 客户端实例
    
    Args:
        provider: LLM 提供商
        api_key: API Key
        model: 模型名称（可选，使用默认）
        **kwargs: 其他参数（如 temperature）
        
    Returns:
        LLM 客户端实例
        
    Raises:
        ValueError: 不支持的提供商
        
    Example:
        >>> client = create_llm_client(LLMProvider.DEEPSEEK, "your_key")
        >>> content, code, exp, symbols = client.unified_chat("双均线策略")
        
        # 切换到 OpenAI
        >>> client = create_llm_client(LLMProvider.OPENAI, "your_key")
    """
    if provider == LLMProvider.DEEPSEEK:
        from .deepseek import DeepSeekClient
        return DeepSeekClient(api_key=api_key, model=model, **kwargs)
    
    elif provider == LLMProvider.OPENAI:
        from .openai_client import OpenAIClient
        return OpenAIClient(api_key=api_key, model=model, **kwargs)
    
    elif provider == LLMProvider.CLAUDE:
        raise NotImplementedError(ErrorMessage.LLM_PROVIDER_NOT_IMPLEMENTED.format(provider="Claude"))
    
    else:
        raise ValueError(ErrorMessage.LLM_PROVIDER_NOT_SUPPORTED.format(provider=provider))

