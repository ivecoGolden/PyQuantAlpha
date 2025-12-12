# tests/test_integration/test_full_flow.py
"""系统完整流程集成测试 (Async)"""

import pytest
import asyncio
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport
from src.api.main import app
from src.api.routes.klines import get_binance_client
from src.api.routes.strategy import get_llm_dependency 
from src.data import Bar

# Mock 依赖
mock_binance = MagicMock()
mock_llm = MagicMock()

def override_get_binance_client():
    return mock_binance

def override_get_llm_client():
    return mock_llm

# 应用覆盖
app.dependency_overrides[get_binance_client] = override_get_binance_client
app.dependency_overrides[get_llm_dependency] = override_get_llm_client

@pytest.fixture(autouse=True)
def setup_mocks():
    """重置并配置 Mock"""
    mock_binance.reset_mock()
    mock_llm.reset_mock()
    
    # Mock Binance Data
    mock_binance.get_klines.return_value = [
        Bar(timestamp=1000000 + i*3600000, open=100.0, high=105.0, low=95.0, close=101.0 + i, volume=1000.0)
        for i in range(100) # 100 根 K 线
    ]
    
    # Mock LLM Response
    mock_llm.generate_strategy.return_value = ('''
class Strategy:
    def init(self):
        self.ma = SMA(10)
    
    def on_bar(self, bar):
        v = self.ma.update(bar.close)
        # 简单的买入逻辑
        if v and bar.close > v:
            self.order("BTCUSDT", "BUY", 0.1)
        elif v and bar.close < v:
            self.close("BTCUSDT")
''', "# 策略解读\n这是一个简单的测试策略。")

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.anyio
class TestSystemIntegration:
    """系统级集成测试"""
    
    async def test_static_resources(self, client):
        """场景 1: 静态资源可访问"""
        # 首页
        res = await client.get("/")
        assert res.status_code == 200
        assert "<title>PyQuantAlpha" in res.text
        
        # JS 文件
        res = await client.get("/static/js/app.js")
        assert res.status_code == 200
    
    async def test_full_backtest_lifecycle(self, client):
        """场景 3: 完整回测流程 (生成 -> 运行 -> 流式结果)"""
        
        # 1. 生成策略
        gen_res = await client.post("/api/generate", json={"prompt": "测试策略"})
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data["is_valid"] is True
        code = gen_data["code"]
        assert "class Strategy" in code
        
        # 2. 启动回测
        run_res = await client.post("/api/backtest/run", json={
            "code": code,
            "symbol": "BTCUSDT",
            "interval": "1h",
            "days": 30
        })
        assert run_res.status_code == 200
        run_data = run_res.json()
        task_id = run_data["task_id"]
        assert task_id
        
        # 3. 监听 SSE 流
        # AsyncClient 的 stream 用法
        async with client.stream("GET", f"/api/backtest/stream/{task_id}") as response:
            assert response.status_code == 200
            
            full_text = ""
            async for line in response.aiter_lines():
                if line:
                    full_text += line + "\n"
                
                # 等待直到收到 total_return，说明 result 的 data 部分也收到了
                if "total_return" in full_text:
                     break
            
            # 验证收到了数据
            assert "event: progress" in full_text
            assert "event: result" in full_text
            assert '"total_return"' in full_text
