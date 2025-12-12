# tests/test_ai/test_chat.py
"""聊天功能测试"""

import pytest
from unittest.mock import patch, MagicMock

from src.ai.base import STRATEGY_KEYWORDS, ChatResult
from src.ai.deepseek import DeepSeekClient
from src.ai.openai_client import OpenAIClient


class TestStrategyKeywords:
    """策略关键词测试"""
    
    def test_keywords_is_list(self):
        """测试关键词是列表类型"""
        assert isinstance(STRATEGY_KEYWORDS, list)
        assert len(STRATEGY_KEYWORDS) > 0
    
    def test_keywords_contain_common_terms(self):
        """测试包含常见策略关键词"""
        assert "策略" in STRATEGY_KEYWORDS
        assert "均线" in STRATEGY_KEYWORDS
        assert "RSI" in STRATEGY_KEYWORDS
        assert "MACD" in STRATEGY_KEYWORDS
    
    def test_keywords_contain_action_terms(self):
        """测试包含交易动作关键词"""
        assert "买入" in STRATEGY_KEYWORDS
        assert "卖出" in STRATEGY_KEYWORDS
        assert "金叉" in STRATEGY_KEYWORDS


class TestIsStrategyRequest:
    """is_strategy_request 方法测试"""
    
    @patch('src.ai.deepseek.OpenAI')
    def test_strategy_request_with_strategy_keyword(self, mock_openai):
        """测试包含'策略'关键词识别为策略请求"""
        client = DeepSeekClient(api_key="test")
        assert client.is_strategy_request("写一个策略") is True
    
    @patch('src.ai.deepseek.OpenAI')
    def test_strategy_request_with_indicator_keyword(self, mock_openai):
        """测试包含指标关键词识别为策略请求"""
        client = DeepSeekClient(api_key="test")
        assert client.is_strategy_request("使用RSI指标") is True
        assert client.is_strategy_request("EMA均线") is True
        assert client.is_strategy_request("MACD金叉") is True
    
    @patch('src.ai.deepseek.OpenAI')
    def test_strategy_request_with_trading_action(self, mock_openai):
        """测试包含交易动作关键词识别为策略请求"""
        client = DeepSeekClient(api_key="test")
        assert client.is_strategy_request("什么时候买入") is True
        assert client.is_strategy_request("止损设置") is True
    
    @patch('src.ai.deepseek.OpenAI')
    def test_chat_request_without_keywords(self, mock_openai):
        """测试不包含关键词识别为普通聊天"""
        client = DeepSeekClient(api_key="test")
        assert client.is_strategy_request("你好") is False
        assert client.is_strategy_request("今天天气怎么样") is False
        assert client.is_strategy_request("什么是量化交易") is False
    
    @patch('src.ai.deepseek.OpenAI')
    def test_case_insensitive(self, mock_openai):
        """测试大小写不敏感"""
        client = DeepSeekClient(api_key="test")
        assert client.is_strategy_request("使用ema做多") is True
        assert client.is_strategy_request("STRATEGY") is True


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


class TestDeepSeekClientChat:
    """DeepSeekClient.chat 方法测试"""
    
    @patch('src.ai.deepseek.OpenAI')
    def test_chat_success(self, mock_openai):
        """测试成功聊天"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好！我是AI助手。"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = DeepSeekClient(api_key="test_key")
        result = client.chat("你好")
        
        assert result == "你好！我是AI助手。"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('src.ai.deepseek.OpenAI')
    def test_chat_api_error(self, mock_openai):
        """测试聊天 API 错误处理"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        client = DeepSeekClient(api_key="test_key")
        
        with pytest.raises(RuntimeError) as exc_info:
            client.chat("测试")
        
        assert "DeepSeek" in str(exc_info.value)


class TestOpenAIClientChat:
    """OpenAIClient.chat 方法测试"""
    
    @patch('src.ai.openai_client.OpenAI')
    def test_chat_success(self, mock_openai):
        """测试成功聊天"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello! I'm GPT."
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test_key")
        result = client.chat("Hi")
        
        assert result == "Hello! I'm GPT."
    
    @patch('src.ai.openai_client.OpenAI')
    def test_chat_api_error(self, mock_openai):
        """测试聊天 API 错误处理"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit")
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test_key")
        
        with pytest.raises(RuntimeError) as exc_info:
            client.chat("测试")
        
        assert "OpenAI" in str(exc_info.value)
