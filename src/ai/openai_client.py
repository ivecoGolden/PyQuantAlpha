# src/ai/openai_client.py
"""OpenAI API 客户端 (预留实现)"""

from openai import OpenAI
from typing import Optional

from .base import BaseLLMClient
from .prompt import SYSTEM_PROMPT
from src.messages import ErrorMessage


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT 客户端
    
    Example:
        >>> client = OpenAIClient(api_key="your_key")
        >>> code = client.generate_strategy("EMA 金叉做多")
    """
    
    DEFAULT_MODEL = "gpt-4o"
    
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> None:
        """初始化客户端
        
        Args:
            api_key: OpenAI API Key
            model: 模型名称，默认 gpt-4o
            temperature: 生成温度，0-1
        """
        self._client = OpenAI(api_key=api_key)
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
            raise RuntimeError(ErrorMessage.LLM_API_FAILED.format(provider="OpenAI", error=str(e)))

