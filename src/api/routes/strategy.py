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

# 策略相关关键词
STRATEGY_KEYWORDS = [
    "策略", "均线", "EMA", "SMA", "RSI", "MACD", "布林", "ATR",
    "买入", "卖出", "做多", "做空", "开仓", "平仓",
    "金叉", "死叉", "突破", "回撤", "止损", "止盈",
    "回测", "指标", "信号", "趋势", "震荡",
    "strategy", "backtest", "indicator", "trade", "order"
]

# 全局实例（延迟初始化，后续可迁移至依赖注入）
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

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    context_code: str | None = Field(None, description="当前策略代码（可选）")

class ChatResponse(BaseModel):
    type: str = Field(..., description="响应类型：chat 或 strategy")
    content: str = Field(..., description="聊天回复或策略代码")
    explanation: str = Field("", description="策略解读（仅 type=strategy）")
    is_valid: bool = Field(True, description="策略是否通过校验（仅 type=strategy）")
    message: str = Field("", description="状态消息")
    symbols: list[str] = Field(default_factory=list, description="涉及的交易对")

class BacktestRequest(BaseModel):
    code: str = Field(..., description="策略代码")
    symbol: str = Field("BTCUSDT", description="交易对 (多资产用逗号分隔)")
    interval: str = Field("1h", description="时间周期")
    days: int = Field(30, description="回测天数")
    # Phase 3.5: 高级配置参数
    initial_capital: float = Field(100000.0, ge=1000, le=1e12, description="初始资金")
    commission_rate: float = Field(0.001, ge=0, le=0.1, description="手续费率")
    slippage: float = Field(0.0005, ge=0, le=0.1, description="滑点")

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

MOCK_CHAT_RESPONSE = "你好！我是 PyQuantAlpha 的 AI 助手。你可以告诉我你想要的交易策略，比如「写一个双均线策略」。"

# ============ 辅助函数 ============

def is_strategy_request(message: str) -> bool:
    """判断是否为策略生成请求 (deprecated - kept for backwards compatibility)"""
    message_lower = message.lower()
    return any(kw.lower() in message_lower for kw in STRATEGY_KEYWORDS)

# ============ 端点 ============

@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    client = Depends(get_llm_dependency)
) -> ChatResponse:
    """统一上下文感知聊天端点
    
    LLM 返回 JSON 格式，自动识别用户意图：
    - type=strategy → 策略生成/修改
    - type=chat → 普通聊天
    """
    message = req.message.strip()
    context_code = req.context_code
    
    # Mock 模式
    if client is None:
        # 使用旧逻辑作为 fallback
        if is_strategy_request(message):
            return ChatResponse(
                type="strategy",
                content=MOCK_STRATEGY_CODE,
                explanation="# Mock 解读\n未配置 API Key。",
                is_valid=True,
                message="[Mock] 返回示例策略"
            )
        else:
            return ChatResponse(
                type="chat",
                content=MOCK_CHAT_RESPONSE,
                message="[Mock] 返回示例回复"
            )
    
    try:
        # 使用统一聊天方法，返回 LLMResponse 对象
        response = client.unified_chat(message, context_code)
        
        if response.is_strategy:
            # 策略生成/修改模式
            is_valid, validation_msg = validate_strategy_code(response.code)
            return ChatResponse(
                type="strategy",
                content=response.code,
                explanation="",
                is_valid=is_valid,
                message="成功" if is_valid else f"校验失败: {validation_msg}",
                symbols=response.symbols
            )
        else:
            # 普通聊天模式
            return ChatResponse(
                type="chat",
                content=response.content,
                message="",
                symbols=response.symbols
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_INTERNAL_ERROR.format(error=str(e)))

class ExplainRequest(BaseModel):
    code: str = Field(..., description="策略代码")

class ExplainResponse(BaseModel):
    explanation: str = Field(..., description="策略解读")

@router.post("/explain", response_model=ExplainResponse)
async def explain_strategy_endpoint(
    req: ExplainRequest,
    client = Depends(get_llm_dependency)
):
    """生成策略解读"""
    if client is None:
        return ExplainResponse(explanation="# Mock 解读\n未配置 API Key。")
    
    try:
        explanation = client.explain_strategy(req.code)
        return ExplainResponse(explanation=explanation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_AI_GENERATE_FAILED.format(error=str(e)))

from src.api.routes.klines import get_binance_client, get_repository
import time

@router.post("/backtest/run", response_model=BacktestStartResponse)
async def run_backtest(
    req: BacktestRequest,
    repo = Depends(get_repository)
):
    """启动回测任务 (异步)
    
    使用 MarketDataRepository 实现透明缓存：
    - 首次请求：从 Binance 拉取 + 写入本地 SQLite
    - 后续请求：直接从本地读取（快 200+ 倍）
    """
    # 1. 校验代码
    is_valid, msg = validate_strategy_code(req.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=ErrorMessage.STRATEGY_INVALID.format(msg=msg))

    # 2. 计算时间范围
    end_time = int(time.time() * 1000)
    start_time = end_time - req.days * 24 * 3600 * 1000

    # 3. 获取数据（透明缓存）
    try:
        if "," in req.symbol:
            # 多资产模式
            symbols = [s.strip() for s in req.symbol.split(",") if s.strip()]
            klines = {}
            for sym in symbols:
                bars, _ = await repo.get_klines(sym, req.interval, start_time, end_time)
                if bars:
                    klines[sym] = bars
            if not klines:
                raise ValueError(ErrorMessage.BACKTEST_DATA_EMPTY)
        else:
            # 单资产模式
            klines, _ = await repo.get_klines(req.symbol, req.interval, start_time, end_time)
    except ValueError as e:
        # 捕获无效交易对等错误
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_INTERNAL_ERROR.format(error=str(e)))
    
    if not klines:
        raise HTTPException(status_code=400, detail=ErrorMessage.BACKTEST_DATA_EMPTY)

    # 4. 构建配置并启动任务
    config = {
        "initial_capital": req.initial_capital,
        "commission_rate": req.commission_rate,
        "slippage": req.slippage,
    }
    task_id = await _backtest_manager.start_backtest(req.code, klines, config)
    
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
