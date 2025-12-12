# src/ai/deepseek.py
"""DeepSeek API 客户端"""

from openai import OpenAI
from typing import Optional

from .base import BaseLLMClient
from src.messages import ErrorMessage


class DeepSeekClient(BaseLLMClient):
    """DeepSeek AI 客户端
    
    使用 OpenAI 兼容 API 调用 DeepSeek 模型。
    
    Example:
        >>> client = DeepSeekClient(api_key="your_key")
        >>> content, code, exp, symbols = client.unified_chat("写一个EMA策略")
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


    def unified_chat(
        self,
        message: str,
        context_code: str | None = None,
        max_tokens: int = 2000
    ) -> "LLMResponse":
        """统一上下文感知聊天
        
        Args:
            message: 用户消息
            context_code: 当前策略代码（可选）
            max_tokens: 最大生成 token 数
            
        Returns:
            LLMResponse 对象
        """
        from .prompt import UNIFIED_SYSTEM_PROMPT
        from .base import LLMResponse
        
        # 构建用户消息
        if context_code:
            user_message = f"""当前策略代码：
```python
{context_code}
```

用户请求：{message}"""
        else:
            user_message = message
        
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": UNIFIED_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=self._temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            
            # 使用 JSON 解析
            return self._parse_json_response(content)
                
        except Exception as e:
            raise RuntimeError(ErrorMessage.LLM_API_FAILED.format(provider="DeepSeek", error=str(e)))


    def explain_strategy(
        self,
        strategy_code: str,
        max_tokens: int = 1000
    ) -> str:
        """生成策略解读"""
        from .prompt import EXPLAIN_SYSTEM_PROMPT
        
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
                    {"role": "user", "content": f"请解读以下策略代码：\n\n```python\n{strategy_code}\n```"}
                ],
                temperature=self._temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(ErrorMessage.LLM_API_FAILED.format(provider="DeepSeek", error=str(e)))
