# src/ai/base.py
"""LLM 客户端抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """LLM JSON 响应解析结果
    
    用于承接 LLM 返回的 JSON 格式响应。
    
    Attributes:
        type: "chat" 或 "strategy"
        content: 回复内容或策略说明
        code: 策略代码（仅 type=strategy 时有值）
        symbols: 涉及的交易对列表
    """
    type: str
    content: str
    code: str | None = None
    symbols: list[str] = field(default_factory=list)
    
    @property
    def is_strategy(self) -> bool:
        """是否为策略响应"""
        return self.type == "strategy" and self.code is not None


@dataclass
class ChatResult:
    """聊天结果（API 层使用）
    
    Attributes:
        type: "chat" 或 "strategy"
        content: 聊天回复或策略代码
        explanation: 策略解读（仅 type=strategy 时有值）
        is_valid: 策略是否通过校验（仅 type=strategy 时有意义）
    """
    type: str
    content: str
    explanation: str = ""
    is_valid: bool = True


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类
    
    所有 LLM 客户端（DeepSeek, OpenAI, Claude 等）都应继承此类。
    需实现 `explain_strategy` 和 `unified_chat` 两个抽象方法。
    """
    
    @abstractmethod
    def explain_strategy(
        self,
        strategy_code: str,
        max_tokens: int = 1000
    ) -> str:
        """生成策略解读
        
        Args:
            strategy_code: 策略 Python 代码
            max_tokens: 最大生成 token 数
            
        Returns:
            策略解读文本
        """
        pass
    
    @abstractmethod
    def unified_chat(
        self,
        message: str,
        context_code: str | None = None,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """统一上下文感知聊天
        
        Args:
            message: 用户消息
            context_code: 当前策略代码（可选）
            max_tokens: 最大生成 token 数
            
        Returns:
            LLMResponse 对象
        """
        pass
    
    def _parse_json_response(self, content: str) -> LLMResponse:
        """解析 JSON 格式的 LLM 响应
        
        Args:
            content: LLM 响应内容（JSON 字符串）
            
        Returns:
            LLMResponse 对象
            
        Raises:
            ValueError: JSON 解析失败
        """
        import json
        from src.messages import ErrorMessage
        
        # 清理 markdown code block 标记
        json_str = content.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        elif json_str.startswith("```"):
            json_str = json_str[3:]
            
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        
        json_str = json_str.strip()
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(ErrorMessage.LLM_INVALID_JSON.format(error=str(e)))
        
        msg_type = data.get("type", "chat")
        msg_content = data.get("content", "")
        symbols = data.get("symbols", [])
        code = data.get("code") if msg_type == "strategy" else None
        
        return LLMResponse(
            type=msg_type,
            content=msg_content,
            code=code,
            symbols=symbols
        )
