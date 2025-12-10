# src/ai/base.py
"""LLM 客户端抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类
    
    所有 LLM 客户端（DeepSeek, OpenAI, Claude 等）都应继承此类。
    
    Example:
        >>> class ClaudeClient(BaseLLMClient):
        ...     def generate_strategy(self, prompt: str) -> str:
        ...         # Claude 特定实现
        ...         pass
    """
    
    @abstractmethod
    def generate_strategy(
        self,
        user_prompt: str,
        max_tokens: int = 2000
    ) -> str:
        """生成策略代码
        
        Args:
            user_prompt: 用户自然语言描述
            max_tokens: 最大生成 token 数
            
        Returns:
            生成的 Python 策略代码
        """
        pass
    
    def _extract_code(self, content: str) -> str:
        """从响应中提取代码块
        
        子类可重写此方法以适应不同模型的输出格式。
        
        Args:
            content: LLM 响应内容
            
        Returns:
            提取的代码字符串
        """
        if content is None:
            return ""
        
        # 处理 markdown 代码块
        if "```python" in content:
            start = content.find("```python") + 9
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        
        return content.strip()
