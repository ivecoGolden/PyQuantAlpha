# tests/test_ai/test_llm_clients.py
"""LLM 客户端测试 (Mock API)"""

import pytest
from unittest.mock import patch, MagicMock

from src.ai.deepseek import DeepSeekClient
from src.ai.openai_client import OpenAIClient
from src.ai.base import BaseLLMClient


class TestBaseLLMClientExtractCode:
    """BaseLLMClient._extract_code 方法测试"""
    
    @patch('src.ai.deepseek.OpenAI')
    def test_extract_code_from_python_block(self, mock_openai):
        """测试从 python 代码块提取代码"""
        client = DeepSeekClient(api_key="test")
        
        content = '''这是一个策略:
```python
class Strategy:
    def init(self):
        pass
```
'''
        result = client._extract_code(content)
        
        assert "class Strategy" in result
        assert "```" not in result
    
    @patch('src.ai.deepseek.OpenAI')
    def test_extract_code_from_generic_block(self, mock_openai):
        """测试从通用代码块提取代码"""
        client = DeepSeekClient(api_key="test")
        
        content = '''```
class Strategy:
    def init(self):
        pass
```'''
        result = client._extract_code(content)
        
        assert "class Strategy" in result
    
    @patch('src.ai.deepseek.OpenAI')
    def test_extract_code_no_block(self, mock_openai):
        """测试无代码块时返回原内容"""
        client = DeepSeekClient(api_key="test")
        
        content = "class Strategy:\n    def init(self): pass"
        result = client._extract_code(content)
        
        assert result == content
    
    @patch('src.ai.deepseek.OpenAI')
    def test_extract_code_none_content(self, mock_openai):
        """测试 None 内容返回空字符串"""
        client = DeepSeekClient(api_key="test")
        
        result = client._extract_code(None)
        
        assert result == ""
    
    @patch('src.ai.deepseek.OpenAI')
    def test_extract_code_strips_whitespace(self, mock_openai):
        """测试提取代码去除首尾空白"""
        client = DeepSeekClient(api_key="test")
        
        content = '''```python

class Strategy:
    pass

```'''
        result = client._extract_code(content)
        
        assert result.startswith("class Strategy")
        assert result.endswith("pass")


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
    
    @patch('src.ai.deepseek.OpenAI')
    def test_generate_strategy_success(self, mock_openai):
        """测试成功生成策略"""
        # Mock API 响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```python
class Strategy:
    def init(self):
        self.ema = EMA(20)
    
    def on_bar(self, bar):
        pass
```'''
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = DeepSeekClient(api_key="test_key")
        code, explanation = client.generate_strategy("EMA 金叉做多")
        
        assert "class Strategy" in code
        assert "def init" in code
        assert "def on_bar" in code
        assert isinstance(explanation, str)
    
    @patch('src.ai.deepseek.OpenAI')
    def test_generate_strategy_api_error(self, mock_openai):
        """测试 API 错误处理"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        client = DeepSeekClient(api_key="test_key")
        
        with pytest.raises(RuntimeError) as exc_info:
            client.generate_strategy("测试 prompt")
        
        assert "DeepSeek" in str(exc_info.value)
        assert "API" in str(exc_info.value)


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
    
    @patch('src.ai.openai_client.OpenAI')
    def test_generate_strategy_success(self, mock_openai):
        """测试成功生成策略"""
        # Mock API 响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```python
class Strategy:
    def init(self):
        self.rsi = RSI(14)
    
    def on_bar(self, bar):
        pass
```'''
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test_key")
        code, explanation = client.generate_strategy("RSI 超卖反弹")
        
        assert "class Strategy" in code
        assert "RSI" in code
        assert isinstance(explanation, str)
    
    @patch('src.ai.openai_client.OpenAI')
    def test_generate_strategy_api_error(self, mock_openai):
        """测试 API 错误处理"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit")
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test_key")
        
        with pytest.raises(RuntimeError) as exc_info:
            client.generate_strategy("测试 prompt")
        
        assert "OpenAI" in str(exc_info.value)


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
