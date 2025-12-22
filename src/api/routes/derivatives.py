# src/api/routes/derivatives.py
"""衍生品数据 API 路由

提供资金费率和市场情绪数据的查询接口。
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import List
import time

from src.data import MarketDataRepository
from src.api.routes.klines import get_repository


router = APIRouter(prefix="/api/data", tags=["derivatives"])


# ============ 响应模型 ============

class FundingRateResponse(BaseModel):
    """资金费率响应"""
    symbol: str
    timestamp: int
    funding_rate: float
    mark_price: float


class SentimentResponse(BaseModel):
    """市场情绪响应"""
    symbol: str
    timestamp: int
    long_short_ratio: float
    long_account_ratio: float
    short_account_ratio: float


class FundingRateListResponse(BaseModel):
    """资金费率列表响应"""
    symbol: str
    count: int
    data: List[FundingRateResponse]


class SentimentListResponse(BaseModel):
    """市场情绪列表响应"""
    symbol: str
    count: int
    data: List[SentimentResponse]


# ============ 路由 ============

@router.get("/funding", response_model=FundingRateListResponse)
async def get_funding_rates(
    symbol: str = Query(..., description="交易对，如 BTCUSDT"),
    days: int = Query(7, ge=1, le=90, description="获取最近 N 天的数据"),
    repo: MarketDataRepository = Depends(get_repository)
):
    """获取资金费率历史
    
    获取指定交易对的资金费率历史数据。
    资金费率每 8 小时结算一次，7 天约 21 条数据。
    
    Args:
        symbol: 交易对
        days: 获取最近 N 天的数据（1-90）
        
    Returns:
        资金费率数据列表
    """
    end_time = int(time.time() * 1000)
    start_time = end_time - days * 24 * 3600 * 1000
    
    try:
        data = await repo.get_funding_rates(symbol, start_time, end_time)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资金费率失败: {e}")
    
    return FundingRateListResponse(
        symbol=symbol,
        count=len(data),
        data=[
            FundingRateResponse(
                symbol=item.symbol,
                timestamp=item.timestamp,
                funding_rate=item.funding_rate,
                mark_price=item.mark_price
            )
            for item in data
        ]
    )


@router.get("/sentiment", response_model=SentimentListResponse)
async def get_sentiment(
    symbol: str = Query(..., description="交易对，如 BTCUSDT"),
    days: int = Query(7, ge=1, le=30, description="获取最近 N 天的数据"),
    period: str = Query("1h", description="统计周期：5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d"),
    repo: MarketDataRepository = Depends(get_repository)
):
    """获取市场情绪（多空比）
    
    获取指定交易对的全局多空账户比历史数据。
    
    Args:
        symbol: 交易对
        days: 获取最近 N 天的数据（1-30）
        period: 统计周期
        
    Returns:
        市场情绪数据列表
    """
    end_time = int(time.time() * 1000)
    start_time = end_time - days * 24 * 3600 * 1000
    
    try:
        data = await repo.get_sentiment(symbol, start_time, end_time, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取市场情绪失败: {e}")
    
    return SentimentListResponse(
        symbol=symbol,
        count=len(data),
        data=[
            SentimentResponse(
                symbol=item.symbol,
                timestamp=item.timestamp,
                long_short_ratio=item.long_short_ratio,
                long_account_ratio=item.long_account_ratio,
                short_account_ratio=item.short_account_ratio
            )
            for item in data
        ]
    )
