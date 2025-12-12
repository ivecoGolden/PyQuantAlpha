# src/ai/deepseek.py
"""DeepSeek API 客户端"""

from openai import OpenAI
from typing import Optional

from .base import BaseLLMClient
from .prompt import SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from src.messages import ErrorMessage


class DeepSeekClient(BaseLLMClient):
    """DeepSeek AI 客户端
    
    使用 OpenAI 兼容 API 调用 DeepSeek 模型。
    
    Example:
        >>> client = DeepSeekClient(api_key="your_key")
        >>> code = client.generate_strategy("EMA 金叉做多")
    """
    
    BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-chat"
    
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> None:
        """初始化客户端
        
        Args:
            api_key: DeepSeek API Key
            model: 模型名称，默认 deepseek-chat
            temperature: 生成温度，0-1
        """
        self._client = OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL
        )
        self._model = model or self.DEFAULT_MODEL
        self._temperature = temperature
    
    def generate_strategy(
        self,
        user_prompt: str,
        max_tokens: int = 2000
    ) -> tuple[str, str]:
        """生成策略代码
        
        Args:
            user_prompt: 用户自然语言描述
            max_tokens: 最大生成 token 数
            
        Returns:
            (code, explanation) 生成的策略代码和解读
            
        Raises:
            RuntimeError: API 调用失败
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self._temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            return self._extract_code_and_explanation(content)
        except Exception as e:
            raise RuntimeError(ErrorMessage.LLM_API_FAILED.format(provider="DeepSeek", error=str(e)))

    def chat(
        self,
        message: str,
        max_tokens: int = 1000
    ) -> str:
        """普通聊天
        
        Args:
            message: 用户消息
            max_tokens: 最大生成 token 数
            
        Returns:
            AI 回复
            
        Raises:
            RuntimeError: API 调用失败
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": message}
                ],
                temperature=self._temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(ErrorMessage.LLM_API_FAILED.format(provider="DeepSeek", error=str(e)))


