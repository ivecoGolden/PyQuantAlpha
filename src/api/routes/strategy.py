# src/api/routes/strategy.py
"""策略相关端点"""

import os
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.ai import LLMProvider, create_llm_client, validate_strategy_code
from src.messages import ErrorMessage
from src.data.binance import BinanceClient
from src.backtest.manager import BacktestManager


router = APIRouter()

# ILLEGAL: Global instances should be managed via dependency injection or singletons
_llm_client = None
_backtest_manager = BacktestManager()

# ============ 依赖项 ============

def get_llm_client():
    """获取 LLM 客户端（延迟初始化）"""
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return None
        
        provider_str = os.getenv("LLM_PROVIDER", "deepseek").lower()
        try:
            provider = LLMProvider(provider_str)
            _llm_client = create_llm_client(provider, api_key=api_key)
        except ValueError:
            return None
    return _llm_client

async def get_llm_dependency():
    return get_llm_client()

# ============ 请求/响应模型 ============

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="用自然语言描述策略")

class GenerateResponse(BaseModel):
    code: str = Field(..., description="生成的策略代码")
    explanation: str = Field(..., description="策略解读")
    message: str = Field(..., description="状态消息")
    is_valid: bool = Field(True, description="代码是否通过校验")

class BacktestRequest(BaseModel):
    code: str = Field(..., description="策略代码")
    symbol: str = Field("BTCUSDT", description="交易对")
    interval: str = Field("1h", description="时间周期")
    days: int = Field(30, description="回测天数")

class BacktestStartResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="消息")

# ============ Mock ============
MOCK_STRATEGY_CODE = '''class Strategy:
    def init(self):
        self.ema20 = EMA(20)
    def on_bar(self, bar):
        v = self.ema20.update(bar.close)
        if v and bar.close > v:
            self.order("BTCUSDT", "BUY", 0.1)
'''

# ============ 端点 ============

@router.post("/generate", response_model=GenerateResponse)
async def generate_strategy(
    req: GenerateRequest,
    client = Depends(get_llm_dependency)
) -> GenerateResponse:
    """AI 生成策略代码"""
    if client is None:
        return GenerateResponse(
            code=MOCK_STRATEGY_CODE,
            explanation="# Mock 解读\n未配置 API Key。",
            message="[Mock] 返回示例策略",
            is_valid=True
        )
    
    try:
        code, explanation = client.generate_strategy(req.prompt)
        is_valid, validation_msg = validate_strategy_code(code)
        
        return GenerateResponse(
            code=code,
            explanation=explanation,
            message="策略生成成功" if is_valid else ErrorMessage.STRATEGY_INVALID.format(msg=validation_msg),
            is_valid=is_valid
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_AI_GENERATE_FAILED.format(error=str(e)))


from src.api.routes.klines import get_binance_client

@router.post("/backtest/run", response_model=BacktestStartResponse)
async def run_backtest(
    req: BacktestRequest,
    data_client: BinanceClient = Depends(get_binance_client)
):
    """启动回测任务 (异步)"""
    # 1. 校验代码
    is_valid, msg = validate_strategy_code(req.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"策略无效: {msg}")

    # 2. 获取数据
    try:
        klines = data_client.get_klines(req.symbol, req.interval, limit=1000)
        # TODO: 处理 days 转换为 limit 或 start_time
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据获取失败: {e}")
    
    if not klines:
        raise HTTPException(status_code=400, detail="未获取到回测数据")

    # 3. 启动任务
    task_id = await _backtest_manager.start_backtest(req.code, klines)
    
    return BacktestStartResponse(
        task_id=task_id,
        message="回测任务已启动"
    )


@router.get("/backtest/stream/{task_id}")
async def stream_backtest(task_id: str):
    """实时回测流 (SSE)"""
    return StreamingResponse(
        _backtest_manager.stream_events(task_id),
        media_type="text/event-stream"
    )
