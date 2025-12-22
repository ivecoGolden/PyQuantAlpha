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
from src.ai.base import LLMResponse

# Mock 依赖 (Global mocks used by overrides)
mock_binance = MagicMock()
mock_llm = MagicMock()

def override_get_binance_client():
    return mock_binance

def override_get_llm_client():
    return mock_llm

TEST_STRATEGY_CODE = '''class Strategy:
    def init(self):
        self.ma = SMA(10)
    
    def on_bar(self, bar):
        v = self.ma.update(bar.close)
        if v and bar.close > v:
            self.order("BTCUSDT", "BUY", 0.1)
        elif v and bar.close < v:
            self.close("BTCUSDT")
'''

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
    
    # Mock LLM unified_chat 返回 LLMResponse
    mock_llm.unified_chat.return_value = LLMResponse(
        type="strategy",
        content="这是一个简单的测试策略",
        code=TEST_STRATEGY_CODE,
        symbols=["BTCUSDT"]
    )

@pytest.fixture
def apply_overrides():
    """应用并清理依赖覆盖"""
    app.dependency_overrides[get_binance_client] = override_get_binance_client
    app.dependency_overrides[get_llm_dependency] = override_get_llm_client
    yield
    # 清理
    app.dependency_overrides.clear()

@pytest.fixture
async def client(apply_overrides):
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
        """场景 3: 完整回测流程 (聊天生成 -> 运行 -> 流式结果)"""
        
        # 1. 通过聊天生成策略
        gen_res = await client.post("/api/chat", json={"message": "写一个简单均线策略"})
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data["type"] == "strategy"
        
        # 加强断言，输出错误原因
        if not gen_data.get("is_valid"):
            pytest.fail(f"策略验证失败: {gen_data.get('error', 'Unknown error')} | Code: {gen_data.get('content')}")
            
        assert gen_data["is_valid"] is True
        code = gen_data["content"]
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
        async with client.stream("GET", f"/api/backtest/stream/{task_id}") as response:
            assert response.status_code == 200
            
            full_text = ""
            async for line in response.aiter_lines():
                if line:
                    full_text += line + "\n"
                
                # 等待直到收到 total_return
                if "total_return" in full_text:
                     break
            
            # 验证收到了结果（快速回测可能跳过进度事件）
            assert "event: result" in full_text
            assert '"total_return"' in full_text
