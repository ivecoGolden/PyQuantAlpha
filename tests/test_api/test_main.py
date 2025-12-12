
# tests/test_api/test_main.py
"""API 端点测试"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.routes.klines import get_binance_client
from src.api.routes.strategy import get_llm_dependency
from src.data import Bar

# 创建 Mock 客户端
mock_client = MagicMock()
mock_llm_client = MagicMock()

def override_get_binance_client():
    return mock_client

def override_get_llm_dependency():
    return mock_llm_client

# 覆盖依赖
app.dependency_overrides[get_binance_client] = override_get_binance_client
app.dependency_overrides[get_llm_dependency] = override_get_llm_dependency

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_mock():
    """每个测试前重置 Mock"""
    mock_client.reset_mock()
    mock_llm_client.reset_mock()
    
    # 设置默认返回值: Binance
    mock_client.get_klines.return_value = [
        Bar(timestamp=1600000000000, open=100.0, high=110.0, low=90.0, close=105.0, volume=1000.0)
        for _ in range(5)
    ]
    mock_client.get_historical_klines.return_value = [
         Bar(timestamp=1600000000000, open=100.0, high=110.0, low=90.0, close=105.0, volume=1000.0)
    ]
    
    # 设置默认返回值: LLM
    mock_llm_client.generate_strategy.return_value = ('''class Strategy:
    def init(self): pass
    def on_bar(self, bar): pass
''', "# Mock 解读")

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
        # 模拟抛出异常
        mock_client.get_klines.side_effect = ValueError("无效的交易对")
        
        response = client.get("/api/klines?symbol=INVALID_XYZ&limit=1")
        assert response.status_code == 400
        assert "无效的交易对" in response.json()["detail"]
        
        # 恢复 side_effect
        mock_client.get_klines.side_effect = None
    
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
        
        # 验证调用了客户端
        mock_client.get_klines.assert_called_with("BTCUSDT", "1h", limit=5)
    
    def test_klines_limit_validation(self):
        """测试 limit 参数验证"""
        # 超出上限 (FastAPI 校验，不进入客户端)
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
        
        # 验证调用了客户端
        mock_client.get_historical_klines.assert_called_with("BTCUSDT", "4h", days=1)


class TestGenerateEndpoint:
    """策略生成端点测试 (Mock)"""
    
    def test_generate_returns_code(self):
        """测试返回策略代码"""
        response = client.post("/api/generate", json={"prompt": "EMA 金叉买入"})
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "explanation" in data
        assert "class Strategy" in data["code"]
    
    def test_generate_requires_prompt(self):
        """测试 prompt 参数必填"""
        response = client.post("/api/generate", json={})
        assert response.status_code == 422


class TestBacktestEndpoint:
    """回测端点测试 (Mock)"""
    
    def test_backtest_starts_task(self):
        """测试启动回测任务"""
        # 使用有效的策略代码（通过校验）
        valid_code = '''
class Strategy:
    def init(self):
        self.value = 0
    
    def on_bar(self, bar):
        self.value += 1
'''
        response = client.post("/api/backtest/run", json={
            "code": valid_code,
            "symbol": "BTCUSDT",
            "interval": "1h",
            "days": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "message" in data
    
    def test_backtest_requires_code(self):
        """测试 code 参数必填"""
        response = client.post("/api/backtest/run", json={})
        assert response.status_code == 422
    
    def test_backtest_invalid_code_returns_400(self):
        """测试无效代码返回 400"""
        response = client.post("/api/backtest/run", json={
            "code": "invalid code",
            "symbol": "BTCUSDT"
        })
        assert response.status_code == 400
