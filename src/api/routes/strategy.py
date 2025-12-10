# src/api/routes/strategy.py
"""策略相关端点 (Mock 占位)"""

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter()


# ============ 请求/响应模型 ============

class GenerateRequest(BaseModel):
    """策略生成请求"""
    prompt: str = Field(..., description="用自然语言描述策略")


class GenerateResponse(BaseModel):
    """策略生成响应"""
    code: str = Field(..., description="生成的策略代码")
    message: str = Field(..., description="状态消息")


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


# ============ 端点实现 ============

@router.post("/generate", response_model=GenerateResponse)
async def generate_strategy(req: GenerateRequest) -> GenerateResponse:
    """AI 生成策略代码
    
    使用 DeepSeek AI 根据自然语言描述生成 Python 策略代码。
    
    **注意**: 当前为 Mock 实现，待 Step 4 完成后替换为真实 AI 生成。
    """
    # Mock 实现
    mock_code = '''class Strategy:
    """AI 生成的策略 (Mock)"""
    
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
    return GenerateResponse(
        code=mock_code,
        message="[Mock] 策略生成功能待 Step 4 实现"
    )


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest) -> BacktestResponse:
    """运行策略回测
    
    对提供的策略代码进行历史回测，返回绩效指标。
    
    **注意**: 当前为 Mock 实现，待 Step 6-7 完成后替换为真实回测。
    """
    # Mock 实现
    return BacktestResponse(
        total_return=0.152,
        max_drawdown=0.083,
        sharpe_ratio=1.45,
        win_rate=0.58,
        total_trades=42
    )
