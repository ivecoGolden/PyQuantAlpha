
# tests/test_api/test_main.py
"""API 端点测试"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.routes.klines import get_binance_client
from src.api.routes.strategy import get_llm_dependency
from src.data import Bar

# 创建 Mock 对象 (Global scope to be accessible, but reset in fixture)
mock_binance = MagicMock()
mock_llm = MagicMock()

@pytest.fixture
def client():
    """TestClient fixture with dependency overrides"""
    # 1. Setup Overrides
    app.dependency_overrides[get_binance_client] = lambda: mock_binance
    app.dependency_overrides[get_llm_dependency] = lambda: mock_llm
    
    # 2. Reset Mocks
    mock_binance.reset_mock()
    mock_llm.reset_mock()
    
    # 设置默认返回值: Binance
    mock_binance.get_klines.return_value = [
        Bar(timestamp=1600000000000 + i*3600000, open=100.0+i, high=110.0+i, low=90.0+i, close=105.0+i, volume=1000.0)
        for i in range(5)
    ]
    mock_binance.get_historical_klines.return_value = [
         Bar(timestamp=1600000000000, open=100.0, high=110.0, low=90.0, close=105.0, volume=1000.0)
    ]
    
    # 设置默认返回值: LLM (Tuple: code, explanation)
    mock_llm.generate_strategy.return_value = ('''class Strategy:
    def init(self): pass
    def on_bar(self, bar): pass
''', "# Mock 解读")
    
    # 3. Create Client
    with TestClient(app) as test_client:
        yield test_client
    
    # 4. Cleanup
    app.dependency_overrides = {}

class TestHealthEndpoint:
    """健康检查端点测试"""
    
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_health_returns_version(self, client):
        response = client.get("/health")
        assert response.json()["version"] == "0.1.0"


class TestKlinesEndpoint:
    """K 线数据端点测试"""
    
    def test_klines_requires_symbol(self, client):
        response = client.get("/api/klines")
        assert response.status_code == 422
    
    def test_klines_invalid_symbol(self, client):
        # 模拟异常
        mock_binance.get_klines.side_effect = ValueError("无效的交易对")
        
        response = client.get("/api/klines?symbol=INVALID_XYZ&limit=1")
        assert response.status_code == 400, f"Response: {response.text}"
        assert "无效的交易对" in response.json()["detail"]
        
        mock_binance.get_klines.side_effect = None
    
    def test_klines_returns_data(self, client):
        response = client.get("/api/klines?symbol=BTCUSDT&interval=1h&limit=5")
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert len(data) == 5
        assert data[0]["open"] == 100.0
        
        mock_binance.get_klines.assert_called_with("BTCUSDT", "1h", limit=5)
    
    def test_klines_limit_validation(self, client):
        response = client.get("/api/klines?symbol=BTCUSDT&limit=2000")
        assert response.status_code == 422


class TestHistoricalKlinesEndpoint:
    """历史 K 线数据端点测试"""
    
    def test_historical_requires_symbol(self, client):
        response = client.get("/api/klines/historical")
        assert response.status_code == 422
    
    def test_historical_returns_data(self, client):
        response = client.get("/api/klines/historical?symbol=BTCUSDT&interval=4h&days=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        mock_binance.get_historical_klines.assert_called_with("BTCUSDT", "4h", days=1)


class TestGenerateEndpoint:
    """策略生成端点测试 (Mock)"""
    
    def test_generate_returns_code(self, client):
        response = client.post("/api/generate", json={"prompt": "EMA 金叉"})
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert "code" in data
        assert "explanation" in data
        assert "class Strategy" in data["code"]
        
        mock_llm.generate_strategy.assert_called()
    
    def test_generate_requires_prompt(self, client):
        response = client.post("/api/generate", json={})
        assert response.status_code == 422


class TestBacktestEndpoint:
    """回测端点测试 (Mock)"""
    
    def test_backtest_starts_task(self, client):
        valid_code = '''
class Strategy:
    def init(self): pass
    def on_bar(self, bar): pass
'''
        # Mock getting data for backtest (using get_historical_klines now)
        mock_binance.get_historical_klines.return_value = [
            Bar(timestamp=1000, open=10, high=11, low=9, close=10, volume=100)
            for _ in range(100)
        ]

        response = client.post("/api/backtest/run", json={
            "code": valid_code,
            "symbol": "BTCUSDT",
            "interval": "1h",
            "days": 30
        })
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert "task_id" in data
        
        # Verify get_historical_klines called
        mock_binance.get_historical_klines.assert_called()

    def test_backtest_requires_code(self, client):
        """测试 code 参数必填"""
        response = client.post("/api/backtest/run", json={})
        assert response.status_code == 422
    
    def test_backtest_invalid_code_returns_400(self, client):
        """测试无效代码返回 400"""
        response = client.post("/api/backtest/run", json={
            "code": "invalid code",
            "symbol": "BTCUSDT"
        })
        assert response.status_code == 400

    def test_backtest_invalid_symbol_returns_400(self, client):
        """测试无效交易对返回 400"""
        valid_code = "class Strategy:\n    def init(self): pass\n    def on_bar(self, bar): pass"
        
        # 模拟抛出 ValueError on get_historical_klines
        mock_binance.get_historical_klines.side_effect = ValueError("Invalid symbol")
        
        response = client.post("/api/backtest/run", json={
            "code": valid_code,
            "symbol": "INVALID",
             "interval": "1h",
            "days": 30
        })
        
        assert response.status_code == 400
        assert "Invalid symbol" in response.json()["detail"]
        
        # 恢复
        mock_binance.get_historical_klines.side_effect = None
