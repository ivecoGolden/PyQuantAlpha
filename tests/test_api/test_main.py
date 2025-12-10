# tests/test_api/test_main.py
"""API 端点测试"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


class TestHealthEndpoint:
    """健康检查端点测试"""
    
    def test_health_returns_ok(self):
        """测试健康检查返回 ok"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
    
    def test_health_returns_version(self):
        """测试健康检查返回版本号"""
        response = client.get("/health")
        assert response.json()["version"] == "0.1.0"


class TestKlinesEndpoint:
    """K 线数据端点测试"""
    
    def test_klines_requires_symbol(self):
        """测试 symbol 参数必填"""
        response = client.get("/api/klines")
        assert response.status_code == 422  # Validation Error
    
    def test_klines_invalid_symbol(self):
        """测试无效交易对返回 400"""
        response = client.get("/api/klines?symbol=INVALID_XYZ&limit=1")
        assert response.status_code == 400
        assert "无效的交易对" in response.json()["detail"]
    
    def test_klines_returns_data(self):
        """测试返回正确的 K 线数据"""
        response = client.get("/api/klines?symbol=BTCUSDT&interval=1h&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        # 验证数据结构
        assert "timestamp" in data[0]
        assert "open" in data[0]
        assert "close" in data[0]
    
    def test_klines_limit_validation(self):
        """测试 limit 参数验证"""
        # 超出上限
        response = client.get("/api/klines?symbol=BTCUSDT&limit=2000")
        assert response.status_code == 422


class TestHistoricalKlinesEndpoint:
    """历史 K 线数据端点测试"""
    
    def test_historical_requires_symbol(self):
        """测试 symbol 参数必填"""
        response = client.get("/api/klines/historical")
        assert response.status_code == 422
    
    def test_historical_returns_data(self):
        """测试返回历史数据"""
        response = client.get("/api/klines/historical?symbol=BTCUSDT&interval=4h&days=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestGenerateEndpoint:
    """策略生成端点测试 (Mock)"""
    
    def test_generate_returns_code(self):
        """测试返回策略代码"""
        response = client.post("/api/generate", json={"prompt": "EMA 金叉买入"})
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "class Strategy" in data["code"]
    
    def test_generate_requires_prompt(self):
        """测试 prompt 参数必填"""
        response = client.post("/api/generate", json={})
        assert response.status_code == 422


class TestBacktestEndpoint:
    """回测端点测试 (Mock)"""
    
    def test_backtest_returns_result(self):
        """测试返回回测结果"""
        response = client.post("/api/backtest", json={
            "code": "class Strategy: pass",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "days": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert "total_return" in data
        assert "max_drawdown" in data
        assert "sharpe_ratio" in data
        assert "win_rate" in data
    
    def test_backtest_requires_code(self):
        """测试 code 参数必填"""
        response = client.post("/api/backtest", json={})
        assert response.status_code == 422
