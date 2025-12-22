# src/data/repository.py
"""
市场数据仓库

实现透明化同步（Lazy Sync）逻辑，提供数据访问的单一入口。
优先从本地数据库读取，缺失时自动从交易所补全。
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, and_, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.database import get_session, Candlestick
from .binance import BinanceClient
from .models import Bar

logger = logging.getLogger(__name__)


class MarketDataRepository:
    """市场数据仓库
    
    提供透明化的数据访问接口，自动处理本地缓存与远程数据同步。
    
    Features:
        - 优先从 SQLite 读取已有数据
        - 自动检测缺失范围并从交易所补全
        - 增量写入 (Upsert) 避免重复
        - 支持部分成功返回（网络故障时）
    
    Example:
        >>> repo = MarketDataRepository()
        >>> bars = await repo.get_klines("BTCUSDT", "1h", start_ts, end_ts)
    """
    
    def __init__(self, client: Optional[BinanceClient] = None) -> None:
        """初始化仓库
        
        Args:
            client: 交易所客户端，默认创建 BinanceClient
        """
        self._client = client or BinanceClient()
    
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
    ) -> Tuple[List[Bar], bool]:
        """获取 K 线数据（透明同步）
        
        1. 检查本地数据库覆盖范围
        2. 若有缺失片段，调用交易所 API 获取（自动分批）
        3. 增量写入数据库
        4. 返回合并后的完整数据
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            interval: 时间周期，如 "1h"
            start_time: 开始时间戳 (毫秒)
            end_time: 结束时间戳 (毫秒)
            
        Returns:
            (bars, is_complete): K 线列表和是否完整标记
            
        Raises:
            ConnectionError: 网络故障且本地无数据时抛出
        """
        # 获取 interval 对应的毫秒数
        from src.data.binance import INTERVAL_MS
        interval_ms = INTERVAL_MS.get(interval, 3600000)  # 默认 1h
        
        async with get_session() as session:
            # Step 1: 查询本地数据
            local_bars = await self._query_local(
                session, symbol, interval, start_time, end_time
            )
            
            # Step 2: 检查覆盖范围
            missing_ranges = self._find_missing_ranges(
                local_bars, start_time, end_time, interval
            )
            
            if not missing_ranges:
                # 本地数据完整
                return local_bars, True
            
            # Step 3: 从交易所补全缺失数据（分批获取）
            is_complete = True
            new_bars: List[Bar] = []
            
            for range_start, range_end in missing_ranges:
                current_start = range_start
                
                # 分批获取，每批最多 1000 条
                while current_start < range_end:
                    try:
                        fetched = self._client.get_klines(
                            symbol=symbol,
                            interval=interval,
                            start_time=current_start,
                            end_time=range_end,
                            limit=1000
                        )
                        
                        if not fetched:
                            break
                        
                        new_bars.extend(fetched)
                        
                        # 下一批从最后一条 K 线之后开始
                        current_start = fetched[-1].timestamp + interval_ms
                        
                    except (ConnectionError, TimeoutError, ValueError) as e:
                        logger.warning(f"获取数据失败: {e}, 范围: {current_start}-{range_end}")
                        is_complete = False
                        break  # 跳过当前 range，继续下一个
            
            # Step 4: 写入数据库
            if new_bars:
                await self._upsert_bars(session, symbol, interval, new_bars)
            
            # Step 5: 重新查询合并后的数据
            all_bars = await self._query_local(
                session, symbol, interval, start_time, end_time
            )
            
            return all_bars, is_complete
    
    async def sync_klines(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
    ) -> int:
        """强制同步 K 线数据
        
        无论本地是否有数据，都从交易所拉取并覆盖。
        
        Args:
            symbol: 交易对
            interval: 时间周期
            start_time: 开始时间戳 (毫秒)
            end_time: 结束时间戳 (毫秒)
            
        Returns:
            同步的 K 线数量
        """
        bars = self._client.get_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
        
        if bars:
            async with get_session() as session:
                await self._upsert_bars(session, symbol, interval, bars)
        
        return len(bars)
    
    async def get_coverage(
        self,
        symbol: str,
        interval: str,
    ) -> Optional[Tuple[int, int]]:
        """获取本地数据覆盖范围
        
        Args:
            symbol: 交易对
            interval: 时间周期
            
        Returns:
            (min_timestamp, max_timestamp) 或 None（无数据时）
        """
        async with get_session() as session:
            stmt = select(
                func.min(Candlestick.timestamp),
                func.max(Candlestick.timestamp)
            ).where(
                and_(
                    Candlestick.symbol == symbol,
                    Candlestick.interval == interval
                )
            )
            
            result = await session.execute(stmt)
            row = result.one()
            
            if row[0] is None:
                return None
            
            return (row[0], row[1])
    
    async def _query_local(
        self,
        session,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
    ) -> List[Bar]:
        """从本地数据库查询 K 线"""
        stmt = select(Candlestick).where(
            and_(
                Candlestick.symbol == symbol,
                Candlestick.interval == interval,
                Candlestick.timestamp >= start_time,
                Candlestick.timestamp <= end_time
            )
        ).order_by(Candlestick.timestamp)
        
        result = await session.execute(stmt)
        rows = result.scalars().all()
        
        return [self._orm_to_bar(row) for row in rows]
    
    async def _upsert_bars(
        self,
        session,
        symbol: str,
        interval: str,
        bars: List[Bar],
    ) -> None:
        """批量插入或更新 K 线数据"""
        for bar in bars:
            stmt = sqlite_insert(Candlestick).values(
                symbol=symbol,
                interval=interval,
                timestamp=bar.timestamp,
                open=Decimal(str(bar.open)),
                high=Decimal(str(bar.high)),
                low=Decimal(str(bar.low)),
                close=Decimal(str(bar.close)),
                volume=Decimal(str(bar.volume)),
                close_time=bar.close_time,
                quote_volume=Decimal(str(bar.quote_volume)),
                trade_count=bar.trade_count,
                taker_buy_base=Decimal(str(bar.taker_buy_base)),
                taker_buy_quote=Decimal(str(bar.taker_buy_quote)),
            ).on_conflict_do_update(
                index_elements=["symbol", "interval", "timestamp"],
                set_={
                    "open": Decimal(str(bar.open)),
                    "high": Decimal(str(bar.high)),
                    "low": Decimal(str(bar.low)),
                    "close": Decimal(str(bar.close)),
                    "volume": Decimal(str(bar.volume)),
                    "close_time": bar.close_time,
                    "quote_volume": Decimal(str(bar.quote_volume)),
                    "trade_count": bar.trade_count,
                    "taker_buy_base": Decimal(str(bar.taker_buy_base)),
                    "taker_buy_quote": Decimal(str(bar.taker_buy_quote)),
                }
            )
            await session.execute(stmt)
    
    def _orm_to_bar(self, row: Candlestick) -> Bar:
        """ORM 对象转换为 Bar"""
        return Bar(
            timestamp=row.timestamp,
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
            close_time=row.close_time,
            quote_volume=float(row.quote_volume),
            trade_count=row.trade_count,
            taker_buy_base=float(row.taker_buy_base),
            taker_buy_quote=float(row.taker_buy_quote),
        )
    
    def _find_missing_ranges(
        self,
        bars: List[Bar],
        start_time: int,
        end_time: int,
        interval: str,
    ) -> List[Tuple[int, int]]:
        """查找缺失的时间范围
        
        基于已有数据和请求范围，计算需要补全的时间段。
        
        简化实现：如果本地数据为空，返回整个范围。
        否则检查头尾是否有缺失。
        """
        if not bars:
            return [(start_time, end_time)]
        
        missing: List[Tuple[int, int]] = []
        
        # 检查头部缺失
        first_ts = bars[0].timestamp
        if first_ts > start_time:
            missing.append((start_time, first_ts - 1))
        
        # 检查尾部缺失
        last_ts = bars[-1].timestamp
        if last_ts < end_time:
            missing.append((last_ts + 1, end_time))
        
        return missing
