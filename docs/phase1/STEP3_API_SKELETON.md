# Step 3: API 骨架开发文档

> **目标**: 创建 FastAPI 应用骨架，实现基础端点，验证 Swagger 文档

---

## 1. 模块结构

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py           # FastAPI 入口
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py     # 健康检查
│   │   ├── klines.py     # K 线数据
│   │   └── strategy.py   # 策略相关 (占位)
│   └── schemas/
│       ├── __init__.py
│       └── responses.py  # 响应模型
```

---

## 2. 端点设计

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 真实 |
| GET | `/api/klines` | 获取 K 线数据 | 真实 (调用 BinanceClient) |
| POST | `/api/generate` | AI 生成策略 | Mock |
| POST | `/api/backtest` | 运行回测 | Mock |

---

## 3. 代码实现

### 3.1 FastAPI 入口

```python
# src/api/main.py
from fastapi import FastAPI
from src.api.routes import health, klines, strategy

app = FastAPI(
    title="PyQuantAlpha API",
    description="AI 量化策略平台 API",
    version="0.1.0"
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(klines.router, prefix="/api", tags=["数据"])
app.include_router(strategy.router, prefix="/api", tags=["策略"])
```

### 3.2 健康检查

```python
# src/api/routes/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "version": "0.1.0"}
```

### 3.3 K 线数据端点

```python
# src/api/routes/klines.py
from fastapi import APIRouter, Query, HTTPException
from typing import List
from src.data import BinanceClient, Bar

router = APIRouter()
client = BinanceClient()

@router.get("/klines", response_model=List[dict])
async def get_klines(
    symbol: str = Query(..., description="交易对，如 BTCUSDT"),
    interval: str = Query("1h", description="时间周期，如 1m, 1h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量")
):
    """获取 K 线数据"""
    try:
        bars = client.get_klines(symbol, interval, limit=limit)
        return [
            {
                "timestamp": bar.timestamp,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume
            }
            for bar in bars
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3.4 策略端点 (Mock)

```python
# src/api/routes/strategy.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str

class GenerateResponse(BaseModel):
    code: str
    message: str

class BacktestRequest(BaseModel):
    code: str
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    days: int = 30

class BacktestResponse(BaseModel):
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int

@router.post("/generate", response_model=GenerateResponse)
async def generate_strategy(req: GenerateRequest):
    """AI 生成策略代码 (Mock)"""
    mock_code = '''class Strategy:
    def init(self):
        self.ema20 = EMA(20)
    
    def on_bar(self, bar):
        self.ema20.update(bar.close)
'''
    return GenerateResponse(
        code=mock_code,
        message="Mock: 策略生成功能待实现"
    )

@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest):
    """运行回测 (Mock)"""
    return BacktestResponse(
        total_return=0.15,
        max_drawdown=0.08,
        sharpe_ratio=1.5,
        win_rate=0.58,
        total_trades=42
    )
```

---

## 4. 启动与验证

### 启动服务

```bash
cd /Users/lixiansheng/Downloads/PyQuantAlpha
uvicorn src.api.main:app --reload --port 8000
```

### 验证端点

1. 打开浏览器访问 http://localhost:8000/docs
2. 查看 Swagger 文档
3. 测试各端点：
   - `GET /health` → 返回 `{"status": "ok"}`
   - `GET /api/klines?symbol=BTCUSDT&interval=1h&limit=5` → 返回 K 线数据
   - `POST /api/generate` → 返回 Mock 策略代码
   - `POST /api/backtest` → 返回 Mock 回测结果

---

## 5. 测试用例

```python
# tests/test_api/test_main.py
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

class TestKlinesEndpoint:
    def test_klines_returns_data(self):
        response = client.get("/api/klines?symbol=BTCUSDT&interval=1h&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
    
    def test_klines_invalid_symbol(self):
        response = client.get("/api/klines?symbol=INVALID&interval=1h&limit=1")
        assert response.status_code == 400

class TestStrategyEndpoints:
    def test_generate_returns_mock(self):
        response = client.post("/api/generate", json={"prompt": "test"})
        assert response.status_code == 200
        assert "class Strategy" in response.json()["code"]
    
    def test_backtest_returns_mock(self):
        response = client.post("/api/backtest", json={"code": "test"})
        assert response.status_code == 200
        assert "total_return" in response.json()
```

---

## 6. 完成标准

- [ ] FastAPI 应用可启动
- [ ] Swagger 文档可访问 (/docs)
- [ ] `/health` 返回正确
- [ ] `/api/klines` 返回真实数据
- [ ] `/api/generate` 返回 Mock
- [ ] `/api/backtest` 返回 Mock
- [ ] 单元测试通过

---

*文档生成日期: 2025-12-10*
