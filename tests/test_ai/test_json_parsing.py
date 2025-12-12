# tests/test_ai/test_json_parsing.py
"""JSON 响应解析测试"""

import pytest
from unittest.mock import patch

from src.ai.deepseek import DeepSeekClient
from src.ai.base import LLMResponse


class TestParseJsonResponse:
    """_parse_json_response 方法测试"""
    
    @patch('src.ai.deepseek.OpenAI')
    def test_parse_valid_strategy_json(self, mock_openai):
        """测试解析有效的策略 JSON"""
        client = DeepSeekClient(api_key="test")
        
        json_content = '''{
            "type": "strategy",
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "content": "这是一个双均线策略",
            "code": "class Strategy:\\n    def init(self):\\n        pass\\n    def on_bar(self, bar):\\n        pass"
        }'''
        
        response = client._parse_json_response(json_content)
        
        assert isinstance(response, LLMResponse)
        assert response.content == "这是一个双均线策略"
        assert response.code is not None
        assert "class Strategy" in response.code
        assert response.symbols == ["BTCUSDT", "ETHUSDT"]
        assert response.is_strategy is True
    
    @patch('src.ai.deepseek.OpenAI')
    def test_parse_valid_chat_json(self, mock_openai):
        """测试解析有效的聊天 JSON"""
        client = DeepSeekClient(api_key="test")
        
        json_content = '''{
            "type": "chat",
            "symbols": [],
            "content": "均线策略是一种趋势跟踪策略"
        }'''
        
        response = client._parse_json_response(json_content)
        
        assert response.content == "均线策略是一种趋势跟踪策略"
        assert response.code is None
        assert response.symbols == []
        assert response.is_strategy is False
    
    @patch('src.ai.deepseek.OpenAI')
    def test_parse_json_with_markdown_wrapper(self, mock_openai):
        """测试解析带有 markdown 包裹的 JSON"""
        client = DeepSeekClient(api_key="test")
        
        json_content = '''```json
{
    "type": "chat",
    "symbols": [],
    "content": "你好！"
}
```'''
        
        response = client._parse_json_response(json_content)
        
        assert response.content == "你好！"
        assert response.code is None
    
    @patch('src.ai.deepseek.OpenAI')
    def test_parse_invalid_json_raises_error(self, mock_openai):
        """测试无效 JSON 抛出 ValueError"""
        client = DeepSeekClient(api_key="test")
        
        invalid_content = "这是一段普通文本，不是 JSON"
        
        with pytest.raises(ValueError) as exc_info:
            client._parse_json_response(invalid_content)
        
        assert "无效的 JSON 格式" in str(exc_info.value)
    
    @patch('src.ai.deepseek.OpenAI')
    def test_parse_json_missing_optional_fields(self, mock_openai):
        """测试解析缺少可选字段的 JSON"""
        client = DeepSeekClient(api_key="test")
        
        json_content = '''{
            "type": "chat",
            "content": "回复内容"
        }'''
        
        response = client._parse_json_response(json_content)
        
        assert response.content == "回复内容"
        assert response.symbols == []  # 默认空数组


class TestLLMResponse:
    """LLMResponse 数据类测试"""
    
    def test_is_strategy_with_code(self):
        """测试有代码时 is_strategy 为 True"""
        response = LLMResponse(
            type="strategy",
            content="说明",
            code="class Strategy: pass",
            symbols=["BTCUSDT"]
        )
        assert response.is_strategy is True
    
    def test_is_strategy_without_code(self):
        """测试无代码时 is_strategy 为 False"""
        response = LLMResponse(
            type="strategy",
            content="说明",
            code=None,
            symbols=[]
        )
        assert response.is_strategy is False
    
    def test_is_strategy_chat_type(self):
        """测试 chat 类型 is_strategy 为 False"""
        response = LLMResponse(
            type="chat",
            content="回复",
            symbols=[]
        )
        assert response.is_strategy is False
