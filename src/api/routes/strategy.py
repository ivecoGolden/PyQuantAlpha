# src/api/routes/strategy.py
"""策略相关端点"""

import os
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.ai import LLMProvider, create_llm_client, validate_strategy_code, STRATEGY_KEYWORDS
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

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")

class ChatResponse(BaseModel):
    type: str = Field(..., description="响应类型：chat 或 strategy")
    content: str = Field(..., description="聊天回复或策略代码")
    explanation: str = Field("", description="策略解读（仅 type=strategy）")
    is_valid: bool = Field(True, description="策略是否通过校验（仅 type=strategy）")
    message: str = Field("", description="状态消息")

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

MOCK_CHAT_RESPONSE = "你好！我是 PyQuantAlpha 的 AI 助手。你可以告诉我你想要的交易策略，比如「写一个双均线策略」。"

# ============ 辅助函数 ============

def is_strategy_request(message: str) -> bool:
    """判断是否为策略生成请求"""
    message_lower = message.lower()
    return any(kw.lower() in message_lower for kw in STRATEGY_KEYWORDS)

# ============ 端点 ============

@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    client = Depends(get_llm_dependency)
) -> ChatResponse:
    """智能聊天端点
    
    自动识别用户意图：
    - 普通聊天：直接返回 AI 回复
    - 策略生成：生成策略代码并校验
    """
    message = req.message.strip()
    
    # 判断意图
    if is_strategy_request(message):
        # 策略生成模式
        if client is None:
            return ChatResponse(
                type="strategy",
                content=MOCK_STRATEGY_CODE,
                explanation="# Mock 解读\n未配置 API Key。",
                is_valid=True,
                message="[Mock] 返回示例策略"
            )
        
        try:
            code, explanation = client.generate_strategy(message)
            is_valid, validation_msg = validate_strategy_code(code)
            
            return ChatResponse(
                type="strategy",
                content=code,
                explanation=explanation,
                is_valid=is_valid,
                message="策略生成成功" if is_valid else f"策略校验失败: {validation_msg}"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"策略生成失败: {str(e)}")
    else:
        # 普通聊天模式
        if client is None:
            return ChatResponse(
                type="chat",
                content=MOCK_CHAT_RESPONSE,
                message="[Mock] 返回示例回复"
            )
        
        try:
            reply = client.chat(message)
            return ChatResponse(
                type="chat",
                content=reply,
                message=""
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")

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
    # 2. 获取数据
    try:
        # 使用 get_historical_klines 支持任意天数的数据获取
        klines = data_client.get_historical_klines(
            symbol=req.symbol, 
            interval=req.interval, 
            days=req.days
        )
    except ValueError as e:
        # 捕获无效交易对等错误
        raise HTTPException(status_code=400, detail=str(e))
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
