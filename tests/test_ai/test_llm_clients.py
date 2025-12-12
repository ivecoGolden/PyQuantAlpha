# tests/test_ai/test_llm_clients.py
"""LLM 客户端测试 (Mock API)"""

import pytest
from unittest.mock import patch, MagicMock

from src.ai.deepseek import DeepSeekClient
from src.ai.openai_client import OpenAIClient
from src.ai.base import BaseLLMClient


class TestDeepSeekClient:
    """DeepSeekClient 测试"""
    
    @patch('src.ai.deepseek.OpenAI')
    def test_init_default_values(self, mock_openai):
        """测试默认初始化值"""
        client = DeepSeekClient(api_key="test_key")
        
        assert client._model == "deepseek-chat"
        assert client._temperature == 0.7
        mock_openai.assert_called_once_with(
            api_key="test_key",
            base_url="https://api.deepseek.com"
        )
    
    @patch('src.ai.deepseek.OpenAI')
    def test_init_custom_values(self, mock_openai):
        """测试自定义初始化值"""
        client = DeepSeekClient(
            api_key="test_key",
            model="deepseek-coder",
            temperature=0.3
        )
        
        assert client._model == "deepseek-coder"
        assert client._temperature == 0.3


class TestOpenAIClient:
    """OpenAIClient 测试"""
    
    @patch('src.ai.openai_client.OpenAI')
    def test_init_default_values(self, mock_openai):
        """测试默认初始化值"""
        client = OpenAIClient(api_key="test_key")
        
        assert client._model == "gpt-4o"
        assert client._temperature == 0.7
        mock_openai.assert_called_once_with(api_key="test_key")
    
    @patch('src.ai.openai_client.OpenAI')
    def test_init_custom_values(self, mock_openai):
        """测试自定义初始化值"""
        client = OpenAIClient(
            api_key="test_key",
            model="gpt-4-turbo",
            temperature=0.5
        )
        
        assert client._model == "gpt-4-turbo"
        assert client._temperature == 0.5


class TestLLMClientInheritance:
    """LLM 客户端继承关系测试"""
    
    @patch('src.ai.deepseek.OpenAI')
    def test_deepseek_inherits_base(self, mock_openai):
        """测试 DeepSeekClient 继承 BaseLLMClient"""
        client = DeepSeekClient(api_key="test")
        assert isinstance(client, BaseLLMClient)
    
    @patch('src.ai.openai_client.OpenAI')
    def test_openai_inherits_base(self, mock_openai):
        """测试 OpenAIClient 继承 BaseLLMClient"""
        client = OpenAIClient(api_key="test")
        assert isinstance(client, BaseLLMClient)
