# tests/test_ai/test_factory.py
"""LLM 工厂函数测试"""

import pytest
from unittest.mock import patch, MagicMock

from src.ai.factory import create_llm_client, LLMProvider
from src.ai.base import BaseLLMClient
from src.ai.deepseek import DeepSeekClient
from src.ai.openai_client import OpenAIClient


class TestLLMProvider:
    """LLMProvider 枚举测试"""
    
    def test_deepseek_value(self):
        """测试 DeepSeek 枚举值"""
        assert LLMProvider.DEEPSEEK.value == "deepseek"
    
    def test_openai_value(self):
        """测试 OpenAI 枚举值"""
        assert LLMProvider.OPENAI.value == "openai"
    
    def test_claude_value(self):
        """测试 Claude 枚举值"""
        assert LLMProvider.CLAUDE.value == "claude"
    
    def test_all_providers_have_lowercase_value(self):
        """测试所有提供商枚举值为小写"""
        for provider in LLMProvider:
            assert provider.value == provider.value.lower()


class TestCreateLLMClientDeepSeek:
    """create_llm_client DeepSeek 分支测试"""
    
    @patch('src.ai.deepseek.OpenAI')
    def test_create_deepseek_client(self, mock_openai):
        """测试创建 DeepSeek 客户端"""
        client = create_llm_client(LLMProvider.DEEPSEEK, "test_api_key")
        
        assert isinstance(client, DeepSeekClient)
        assert isinstance(client, BaseLLMClient)
    
    @patch('src.ai.deepseek.OpenAI')
    def test_deepseek_with_custom_model(self, mock_openai):
        """测试自定义模型"""
        client = create_llm_client(
            LLMProvider.DEEPSEEK, 
            "test_api_key", 
            model="deepseek-coder"
        )
        
        assert client._model == "deepseek-coder"
    
    @patch('src.ai.deepseek.OpenAI')
    def test_deepseek_with_temperature(self, mock_openai):
        """测试自定义温度"""
        client = create_llm_client(
            LLMProvider.DEEPSEEK, 
            "test_api_key", 
            temperature=0.5
        )
        
        assert client._temperature == 0.5
    
    @patch('src.ai.deepseek.OpenAI')
    def test_deepseek_default_model(self, mock_openai):
        """测试默认模型"""
        client = create_llm_client(LLMProvider.DEEPSEEK, "test_api_key")
        
        assert client._model == DeepSeekClient.DEFAULT_MODEL


class TestCreateLLMClientOpenAI:
    """create_llm_client OpenAI 分支测试"""
    
    @patch('src.ai.openai_client.OpenAI')
    def test_create_openai_client(self, mock_openai):
        """测试创建 OpenAI 客户端"""
        client = create_llm_client(LLMProvider.OPENAI, "test_api_key")
        
        assert isinstance(client, OpenAIClient)
        assert isinstance(client, BaseLLMClient)
    
    @patch('src.ai.openai_client.OpenAI')
    def test_openai_with_custom_model(self, mock_openai):
        """测试自定义模型"""
        client = create_llm_client(
            LLMProvider.OPENAI, 
            "test_api_key", 
            model="gpt-4-turbo"
        )
        
        assert client._model == "gpt-4-turbo"
    
    @patch('src.ai.openai_client.OpenAI')
    def test_openai_default_model(self, mock_openai):
        """测试默认模型"""
        client = create_llm_client(LLMProvider.OPENAI, "test_api_key")
        
        assert client._model == OpenAIClient.DEFAULT_MODEL


class TestCreateLLMClientErrors:
    """create_llm_client 错误处理测试"""
    
    def test_claude_not_implemented(self):
        """测试 Claude 尚未实现"""
        with pytest.raises(NotImplementedError) as exc_info:
            create_llm_client(LLMProvider.CLAUDE, "test_api_key")
        
        assert "Claude" in str(exc_info.value)
    
    def test_invalid_provider_raises_value_error(self):
        """测试无效提供商抛出 ValueError"""
        # 使用字符串模拟无效提供商
        with pytest.raises((ValueError, AttributeError)):
            create_llm_client("invalid_provider", "test_api_key")
