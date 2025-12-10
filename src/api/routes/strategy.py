# src/api/routes/strategy.py
"""策略相关端点"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.ai import LLMProvider, create_llm_client, validate_strategy_code
from src.messages import ErrorMessage


router = APIRouter()

# LLM 客户端（延迟初始化）
_llm_client = None


def get_llm_client():
    """获取 LLM 客户端（延迟初始化）"""
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return None  # 没有 API Key，使用 Mock
        
        # 使用工厂方法创建客户端，便于切换模型
        provider_str = os.getenv("LLM_PROVIDER", "deepseek").lower()
        try:
            provider = LLMProvider(provider_str)
            _llm_client = create_llm_client(provider, api_key=api_key)
        except ValueError:
            return None
    return _llm_client


# ============ 请求/响应模型 ============

class GenerateRequest(BaseModel):
    """策略生成请求"""
    prompt: str = Field(..., description="用自然语言描述策略")


class GenerateResponse(BaseModel):
    """策略生成响应"""
    code: str = Field(..., description="生成的策略代码")
    message: str = Field(..., description="状态消息")
    is_valid: bool = Field(True, description="代码是否通过校验")


class BacktestRequest(BaseModel):
    """回测请求"""
    code: str = Field(..., description="策略代码")
    symbol: str = Field("BTCUSDT", description="交易对")
    interval: str = Field("1h", description="时间周期")
    days: int = Field(30, ge=1, le=365, description="回测天数")


class BacktestResponse(BaseModel):
    """回测响应"""
    total_return: float = Field(..., description="总收益率")
    max_drawdown: float = Field(..., description="最大回撤")
    sharpe_ratio: float = Field(..., description="夏普比率")
    win_rate: float = Field(..., description="胜率")
    total_trades: int = Field(..., description="总交易次数")


# ============ Mock 策略代码 ============

MOCK_STRATEGY_CODE = '''class Strategy:
    """AI 生成的策略"""
    
    def init(self):
        self.ema20 = EMA(20)
        self.ema60 = EMA(60)
        self.prev_fast = None
    
    def on_bar(self, bar):
        fast = self.ema20.update(bar.close)
        slow = self.ema60.update(bar.close)
        
        # 金叉买入
        if self.prev_fast and self.prev_fast < slow and fast > slow:
            self.order("BTCUSDT", "BUY", 0.1)
        
        # 死叉卖出
        if self.prev_fast and self.prev_fast > slow and fast < slow:
            self.close("BTCUSDT")
        
        self.prev_fast = fast
'''


# ============ 端点实现 ============

@router.post("/generate", response_model=GenerateResponse)
async def generate_strategy(req: GenerateRequest) -> GenerateResponse:
    """AI 生成策略代码
    
    使用 DeepSeek AI 根据自然语言描述生成 Python 策略代码。
    
    若未配置 DEEPSEEK_API_KEY，将返回 Mock 策略代码。
    """
    client = get_llm_client()
    
    # 如果没有配置 API Key，使用 Mock
    if client is None:
        return GenerateResponse(
            code=MOCK_STRATEGY_CODE,
            message="[Mock] 未配置 DEEPSEEK_API_KEY，返回示例策略",
            is_valid=True
        )
    
    # 调用 AI 生成策略
    try:
        code = client.generate_strategy(req.prompt)
        
        # 验证生成的代码
        is_valid, validation_msg = validate_strategy_code(code)
        
        if is_valid:
            return GenerateResponse(
                code=code,
                message="策略生成成功",
                is_valid=True
            )
        else:
            return GenerateResponse(
                code=code,
                message=ErrorMessage.STRATEGY_INVALID.format(msg=validation_msg),
                is_valid=False
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_AI_GENERATE_FAILED.format(error=str(e)))


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest) -> BacktestResponse:
    """运行策略回测
    
    对提供的策略代码进行历史回测，返回绩效指标。
    
    **注意**: 当前为 Mock 实现，待 Step 6-7 完成后替换为真实回测。
    """
    # 先验证代码
    is_valid, validation_msg = validate_strategy_code(req.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=ErrorMessage.STRATEGY_INVALID.format(msg=validation_msg))
    
    # Mock 实现
    return BacktestResponse(
        total_return=0.152,
        max_drawdown=0.083,
        sharpe_ratio=1.45,
        win_rate=0.58,
        total_trades=42
    )

