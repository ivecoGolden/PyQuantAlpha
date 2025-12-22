# src/api/routes/klines.py
"""K 线数据相关端点

Phase 3 升级：
- 集成 MarketDataRepository 透明缓存
- 新增 POST /api/klines/sync 手动同步接口
- 支持返回完整 11 字段数据
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends, Body
from functools import lru_cache
from pydantic import BaseModel

from src.data import BinanceClient, MarketDataRepository
from src.database import init_db
from src.messages import ErrorMessage


router = APIRouter()


# === 依赖注入 ===

@lru_cache()
def get_binance_client() -> BinanceClient:
    """获取 Binance 客户端实例 (依赖注入)"""
    return BinanceClient()


@lru_cache()
def get_repository() -> MarketDataRepository:
    """获取数据仓库实例 (依赖注入)"""
    return MarketDataRepository()


# === 请求/响应模型 ===

class SyncRequest(BaseModel):
    """同步请求参数"""
    symbol: str
    interval: str
    start_time: int
    end_time: int


class SyncResponse(BaseModel):
    """同步响应"""
    synced_count: int
    symbol: str
    interval: str


class KlineResponse(BaseModel):
    """K 线响应（完整字段）"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_volume: float
    trade_count: int
    taker_buy_base: float
    taker_buy_quote: float


# === API 端点 ===

@router.get("/klines")
async def get_klines(
    symbol: str = Query(..., description="交易对，如 BTCUSDT"),
    interval: str = Query("1h", description="时间周期，如 1m, 1h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量，最大 1000"),
    full: bool = Query(False, description="是否返回完整字段"),
    client: BinanceClient = Depends(get_binance_client)
) -> List[dict]:
    """获取 K 线数据
    
    从 Binance API 获取指定交易对的 K 线数据。
    
    Args:
        symbol: 交易对，如 BTCUSDT
        interval: 时间周期，如 1m, 5m, 15m, 1h, 4h, 1d
        limit: 返回数量，1-1000
        full: 是否返回完整 11 字段，默认 False 仅返回 OHLCV
        
    Returns:
        K 线数据列表
    """
    try:
        bars = client.get_klines(symbol, interval, limit=limit)
        
        if full:
            return [bar.to_dict() for bar in bars]
        else:
            return [bar.to_basic_dict() for bar in bars]
            
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
    days: int = Query(7, ge=1, le=365, description="获取最近 N 天的数据"),
    full: bool = Query(False, description="是否返回完整字段"),
    client: BinanceClient = Depends(get_binance_client)
) -> List[dict]:
    """获取历史 K 线数据
    
    批量获取指定天数的历史 K 线数据。
    
    Args:
        symbol: 交易对
        interval: 时间周期
        days: 获取最近 N 天的数据
        full: 是否返回完整 11 字段
        
    Returns:
        K 线数据列表
    """
    try:
        bars = client.get_historical_klines(symbol, interval, days=days)
        
        if full:
            return [bar.to_dict() for bar in bars]
        else:
            return [bar.to_basic_dict() for bar in bars]
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_INTERNAL_ERROR.format(error=str(e)))


@router.post("/klines/sync")
async def sync_klines(
    request: SyncRequest,
    repo: MarketDataRepository = Depends(get_repository)
) -> SyncResponse:
    """手动同步 K 线数据
    
    强制从交易所拉取指定范围的数据并写入本地数据库。
    用于预热缓存或定时任务批量同步。
    
    Args:
        request: 同步请求参数
        
    Returns:
        同步结果
    """
    try:
        # 确保数据库已初始化
        await init_db()
        
        count = await repo.sync_klines(
            symbol=request.symbol,
            interval=request.interval,
            start_time=request.start_time,
            end_time=request.end_time,
        )
        
        return SyncResponse(
            synced_count=count,
            symbol=request.symbol,
            interval=request.interval,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_INTERNAL_ERROR.format(error=str(e)))


@router.get("/klines/coverage")
async def get_coverage(
    symbol: str = Query(..., description="交易对"),
    interval: str = Query(..., description="时间周期"),
    repo: MarketDataRepository = Depends(get_repository)
) -> dict:
    """查询本地数据覆盖范围
    
    返回指定交易对和周期在本地数据库中的时间范围。
    
    Args:
        symbol: 交易对
        interval: 时间周期
        
    Returns:
        覆盖范围信息
    """
    try:
        await init_db()
        coverage = await repo.get_coverage(symbol, interval)
        
        if coverage is None:
            return {
                "symbol": symbol,
                "interval": interval,
                "has_data": False,
                "min_timestamp": None,
                "max_timestamp": None,
            }
        
        return {
            "symbol": symbol,
            "interval": interval,
            "has_data": True,
            "min_timestamp": coverage[0],
            "max_timestamp": coverage[1],
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorMessage.HTTP_INTERNAL_ERROR.format(error=str(e)))
