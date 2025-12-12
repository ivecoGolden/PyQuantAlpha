# tests/test_ai/test_chat.py
"""聊天功能测试"""

from src.ai.base import ChatResult


class TestChatResult:
    """ChatResult 数据类测试"""
    
    def test_chat_result_creation(self):
        """测试创建 ChatResult"""
        result = ChatResult(
            type="chat",
            content="你好！"
        )
        assert result.type == "chat"
        assert result.content == "你好！"
        assert result.explanation == ""
        assert result.is_valid is True
    
    def test_strategy_result_creation(self):
        """测试创建策略类型 ChatResult"""
        result = ChatResult(
            type="strategy",
            content="class Strategy: pass",
            explanation="这是一个简单策略",
            is_valid=True
        )
        assert result.type == "strategy"
        assert result.content == "class Strategy: pass"
        assert result.explanation == "这是一个简单策略"
