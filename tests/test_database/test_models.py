# tests/test_database/test_models.py
"""Candlestick ORM 模型测试"""

import pytest
from decimal import Decimal

from src.database.models import Candlestick
from src.database import get_session, init_db


class TestCandlestickModel:
    """测试 Candlestick ORM 模型"""
    
    def test_tablename(self):
        """测试表名"""
        assert Candlestick.__tablename__ == "candlesticks"
    
    def test_create_instance(self):
        """测试创建实例"""
        candle = Candlestick(
            symbol="BTCUSDT",
            interval="1h",
            timestamp=1609459200000,
            open=Decimal("29000.0"),
            high=Decimal("29500.0"),
            low=Decimal("28800.0"),
            close=Decimal("29300.0"),
            volume=Decimal("1000.0"),
            close_time=1609462799999,
            quote_volume=Decimal("29300000.0"),
            trade_count=5000,
            taker_buy_base=Decimal("600.0"),
            taker_buy_quote=Decimal("17580000.0"),
        )
        
        assert candle.symbol == "BTCUSDT"
        assert candle.interval == "1h"
        assert candle.close == Decimal("29300.0")
    
    def test_repr(self):
        """测试字符串表示"""
        candle = Candlestick(
            symbol="ETHUSDT",
            interval="4h",
            timestamp=1609459200000,
            open=Decimal("700.0"),
            high=Decimal("720.0"),
            low=Decimal("690.0"),
            close=Decimal("715.0"),
            volume=Decimal("5000.0"),
            close_time=1609473599999,
            quote_volume=Decimal("3575000.0"),
            trade_count=2000,
            taker_buy_base=Decimal("2500.0"),
            taker_buy_quote=Decimal("1787500.0"),
        )
        
        repr_str = repr(candle)
        assert "ETHUSDT" in repr_str
        assert "4h" in repr_str
        assert "715" in repr_str


class TestCandlestickCRUD:
    """测试 Candlestick CRUD 操作"""
    
    @pytest.mark.asyncio
    async def test_insert_and_query(self):
        """测试插入和查询"""
        from sqlalchemy import select
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        import time
        await init_db()
        
        # 使用唯一时间戳避免测试冲突
        unique_ts = int(time.time() * 1000)
        
        async with get_session() as session:
            # 使用 upsert 避免重复插入冲突
            stmt = sqlite_insert(Candlestick).values(
                symbol="TESTBTC",
                interval="1h",
                timestamp=unique_ts,
                open=Decimal("35000.0"),
                high=Decimal("35500.0"),
                low=Decimal("34800.0"),
                close=Decimal("35200.0"),
                volume=Decimal("1234.56"),
                close_time=unique_ts + 3599999,
                quote_volume=Decimal("43456000.0"),
                trade_count=8000,
                taker_buy_base=Decimal("700.0"),
                taker_buy_quote=Decimal("24640000.0"),
            ).on_conflict_do_update(
                index_elements=["symbol", "interval", "timestamp"],
                set_={"close": Decimal("35200.0")}
            )
            await session.execute(stmt)
            await session.commit()
            
            # 查询
            query = select(Candlestick).where(
                Candlestick.symbol == "TESTBTC",
                Candlestick.interval == "1h",
                Candlestick.timestamp == unique_ts
            )
            result = await session.execute(query)
            found = result.scalar_one()
            
            assert found.close == Decimal("35200.0")
            assert found.trade_count == 8000
    
    @pytest.mark.asyncio
    async def test_composite_primary_key(self):
        """测试复合主键唯一性"""
        from sqlalchemy import select
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        import time
        await init_db()
        
        # 使用唯一时间戳
        unique_ts = int(time.time() * 1000) + 1000000
        
        async with get_session() as session:
            # 第一次插入
            stmt1 = sqlite_insert(Candlestick).values(
                symbol="TESTETH",
                interval="1h",
                timestamp=unique_ts,
                open=Decimal("2000.0"),
                high=Decimal("2050.0"),
                low=Decimal("1980.0"),
                close=Decimal("2020.0"),
                volume=Decimal("500.0"),
                close_time=unique_ts + 3599999,
                quote_volume=Decimal("1010000.0"),
                trade_count=1000,
                taker_buy_base=Decimal("250.0"),
                taker_buy_quote=Decimal("505000.0"),
            ).on_conflict_do_nothing()
            await session.execute(stmt1)
            
            # 相同主键更新（upsert）
            stmt2 = sqlite_insert(Candlestick).values(
                symbol="TESTETH",
                interval="1h",
                timestamp=unique_ts,
                open=Decimal("2000.0"),
                high=Decimal("2100.0"),  # 更新
                low=Decimal("1980.0"),
                close=Decimal("2080.0"),  # 更新
                volume=Decimal("600.0"),  # 更新
                close_time=unique_ts + 3599999,
                quote_volume=Decimal("1248000.0"),
                trade_count=1200,
                taker_buy_base=Decimal("300.0"),
                taker_buy_quote=Decimal("624000.0"),
            ).on_conflict_do_update(
                index_elements=["symbol", "interval", "timestamp"],
                set_={"close": Decimal("2080.0"), "high": Decimal("2100.0")}
            )
            await session.execute(stmt2)
            await session.commit()
            
            # 验证只有一条记录且已更新
            query = select(Candlestick).where(
                Candlestick.symbol == "TESTETH",
                Candlestick.timestamp == unique_ts
            )
            result = await session.execute(query)
            records = result.scalars().all()
            
            assert len(records) == 1
            assert records[0].close == Decimal("2080.0")
            assert records[0].high == Decimal("2100.0")


class TestFundingRateModel:
    """测试 FundingRate ORM 模型"""
    
    def test_tablename(self):
        """测试表名"""
        from src.database.models import FundingRate
        assert FundingRate.__tablename__ == "funding_rates"
    
    def test_create_instance(self):
        """测试创建实例"""
        from src.database.models import FundingRate
        rate = FundingRate(
            symbol="BTCUSDT",
            timestamp=1700000000000,
            funding_rate=Decimal("0.0001"),
            mark_price=Decimal("35000.0")
        )
        assert rate.symbol == "BTCUSDT"
        assert rate.funding_rate == Decimal("0.0001")
    
    def test_repr(self):
        """测试字符串表示"""
        from src.database.models import FundingRate
        rate = FundingRate(
            symbol="ETHUSDT",
            timestamp=1700000000000,
            funding_rate=Decimal("0.00015"),
            mark_price=Decimal("2000.0")
        )
        repr_str = repr(rate)
        assert "ETHUSDT" in repr_str
        assert "0.00015" in repr_str


class TestMarketSentimentModel:
    """测试 MarketSentiment ORM 模型"""
    
    def test_tablename(self):
        """测试表名"""
        from src.database.models import MarketSentiment
        assert MarketSentiment.__tablename__ == "market_sentiment"
    
    def test_create_instance(self):
        """测试创建实例"""
        from src.database.models import MarketSentiment
        sentiment = MarketSentiment(
            symbol="BTCUSDT",
            timestamp=1700000000000,
            long_short_ratio=Decimal("1.25"),
            long_account_ratio=Decimal("0.5556"),
            short_account_ratio=Decimal("0.4444")
        )
        assert sentiment.symbol == "BTCUSDT"
        assert sentiment.long_short_ratio == Decimal("1.25")
    
    def test_repr(self):
        """测试字符串表示"""
        from src.database.models import MarketSentiment
        sentiment = MarketSentiment(
            symbol="BTCUSDT",
            timestamp=1700000000000,
            long_short_ratio=Decimal("0.85"),
            long_account_ratio=Decimal("0.46"),
            short_account_ratio=Decimal("0.54")
        )
        repr_str = repr(sentiment)
        assert "BTCUSDT" in repr_str
        assert "0.85" in repr_str
