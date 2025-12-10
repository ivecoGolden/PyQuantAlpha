# src/api/routes/klines.py
"""K 线数据相关端点"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException

from src.data import BinanceClient
from src.messages import ErrorMessage


router = APIRouter()

# 创建客户端实例
_client = BinanceClient(timeout=30)


@router.get("/klines")
async def get_klines(
    symbol: str = Query(..., description="交易对，如 BTCUSDT"),
    interval: str = Query("1h", description="时间周期，如 1m, 1h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量，最大 1000")
) -> List[dict]:
    """获取 K 线数据
    
    从 Binance API 获取指定交易对的 K 线数据。
    
    Args:
        symbol: 交易对，如 BTCUSDT
        interval: 时间周期，如 1m, 5m, 15m, 1h, 4h, 1d
        limit: 返回数量，1-1000
        
    Returns:
        K 线数据列表
    """
    try:
        bars = _client.get_klines(symbol, interval, limit=limit)
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
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_INTERNAL_ERROR.format(error=str(e)))


@router.get("/klines/historical")
async def get_historical_klines(
    symbol: str = Query(..., description="交易对，如 BTCUSDT"),
    interval: str = Query("1h", description="时间周期"),
    days: int = Query(7, ge=1, le=365, description="获取最近 N 天的数据")
) -> List[dict]:
    """获取历史 K 线数据
    
    批量获取指定天数的历史 K 线数据。
    
    Args:
        symbol: 交易对
        interval: 时间周期
        days: 获取最近 N 天的数据
        
    Returns:
        K 线数据列表
    """
    try:
        bars = _client.get_historical_klines(symbol, interval, days=days)
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
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_INTERNAL_ERROR.format(error=str(e)))
