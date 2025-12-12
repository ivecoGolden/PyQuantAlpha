# tests/test_api/test_strategy_routes.py
"""策略路由端点测试"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


class TestChatEndpoint:
    """/api/chat 端点测试"""
    
    def test_chat_endpoint_exists(self):
        """测试端点存在"""
        response = client.post("/api/chat", json={"message": "你好"})
        # 即使没有 API key，也应该返回 mock 响应而不是 404
        assert response.status_code != 404
    
    def test_chat_normal_message_returns_chat_type(self):
        """测试普通消息返回 chat 类型"""
        response = client.post("/api/chat", json={"message": "你好"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "chat"
        assert "content" in data
    
    def test_chat_strategy_message_returns_strategy_type(self):
        """测试策略消息返回 strategy 类型"""
        response = client.post("/api/chat", json={"message": "写一个双均线策略"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "strategy"
        assert "content" in data
        assert "explanation" in data
    
    def test_chat_empty_message(self):
        """测试空消息处理"""
        response = client.post("/api/chat", json={"message": ""})
        # 空消息应该作为普通聊天处理
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "chat"
    
    def test_chat_missing_message_field(self):
        """测试缺少 message 字段"""
        response = client.post("/api/chat", json={})
        assert response.status_code == 422  # Validation Error


class TestIsStrategyRequestFunction:
    """is_strategy_request 函数独立测试"""
    
    def test_import_function(self):
        """测试函数可导入"""
        from src.api.routes.strategy import is_strategy_request
        assert callable(is_strategy_request)
    
    def test_strategy_keywords_detection(self):
        """测试策略关键词检测"""
        from src.api.routes.strategy import is_strategy_request
        
        # 策略相关
        assert is_strategy_request("写一个策略") is True
        assert is_strategy_request("使用RSI") is True
        assert is_strategy_request("MACD指标") is True
        assert is_strategy_request("金叉买入") is True
        
        # 普通聊天
        assert is_strategy_request("你好") is False
        assert is_strategy_request("今天天气") is False
