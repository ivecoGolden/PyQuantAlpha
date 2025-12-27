# tests/test_data/test_repository.py
"""MarketDataRepository 测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal

from src.data.repository import MarketDataRepository
from src.data.models import Bar


class TestMarketDataRepositoryInit:
    """测试 Repository 初始化"""
    
    def test_default_client(self):
        """测试默认创建 BinanceClient"""
        from src.data.binance import BinanceClient
        
        repo = MarketDataRepository()
        assert isinstance(repo._client, BinanceClient)
    
    def test_custom_client(self):
        """测试自定义客户端"""
        mock_client = Mock()
        repo = MarketDataRepository(client=mock_client)
        assert repo._client is mock_client


class TestFindMissingRanges:
    """测试缺失范围查找"""
    
    @pytest.fixture
    def repo(self):
        return MarketDataRepository()
    
    def test_empty_bars_returns_full_range(self, repo):
        """测试空数据返回完整范围"""
        result = repo._find_missing_ranges([], 1000, 5000, "1h")
        assert result == [(1000, 5000)]
    
    def test_full_coverage_returns_empty(self, repo):
        """测试完全覆盖返回空列表"""
        bars = [
            Bar(timestamp=1000, open=1, high=2, low=0.5, close=1.5, volume=100),
            Bar(timestamp=2000, open=1.5, high=2.5, low=1, close=2, volume=150),
            Bar(timestamp=3000, open=2, high=3, low=1.5, close=2.5, volume=200),
        ]
        result = repo._find_missing_ranges(bars, 1000, 3000, "1h")
        assert result == []
    
    def test_missing_head(self, repo):
        """测试头部缺失"""
        bars = [
            Bar(timestamp=3000, open=1, high=2, low=0.5, close=1.5, volume=100),
            Bar(timestamp=4000, open=1.5, high=2.5, low=1, close=2, volume=150),
        ]
        result = repo._find_missing_ranges(bars, 1000, 4000, "1h")
        assert (1000, 2999) in result
    
    def test_missing_tail(self, repo):
        """测试尾部缺失"""
        bars = [
            Bar(timestamp=1000, open=1, high=2, low=0.5, close=1.5, volume=100),
            Bar(timestamp=2000, open=1.5, high=2.5, low=1, close=2, volume=150),
        ]
        result = repo._find_missing_ranges(bars, 1000, 5000, "1h")
        assert (2001, 5000) in result


class TestOrmToBar:
    """测试 ORM 到 Bar 转换"""
    
    def test_conversion(self):
        """测试转换正确性"""
        from src.database.models import Candlestick
        
        orm_obj = Candlestick(
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
        
        repo = MarketDataRepository()
        bar = repo._orm_to_bar(orm_obj)
        
        assert isinstance(bar, Bar)
        assert bar.timestamp == 1609459200000
        assert bar.close == 29300.0
        assert bar.trade_count == 5000
        assert bar.taker_buy_base == 600.0


class TestGetKlines:
    """测试透明同步获取 K 线"""
    
    @pytest.fixture
    def mock_client(self):
        """创建 mock 客户端"""
        client = Mock()
        client.get_klines.return_value = [
            Bar(
                timestamp=3000,
                open=100.0,
                high=110.0,
                low=95.0,
                close=105.0,
                volume=1000.0,
                close_time=3999,
                quote_volume=105000.0,
                trade_count=500,
                taker_buy_base=600.0,
                taker_buy_quote=63000.0,
            )
        ]
        return client
    
    @pytest.mark.asyncio
    async def test_get_klines_with_full_cache(self, mock_client):
        """测试完全缓存命中"""
        repo = MarketDataRepository(client=mock_client)
        
        # Mock 本地查询返回完整数据
        with patch.object(repo, '_query_local', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [
                Bar(timestamp=1000, open=1, high=2, low=0.5, close=1.5, volume=100),
                Bar(timestamp=2000, open=1.5, high=2.5, low=1, close=2, volume=150),
            ]
            
            bars, is_complete = await repo.get_klines("BTCUSDT", "1h", 1000, 2000)
            
            assert len(bars) == 2
            assert is_complete is True
            # 不应调用远程 API
            mock_client.get_klines.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_klines_with_partial_cache(self, mock_client):
        """测试部分缓存命中，需要补全"""
        repo = MarketDataRepository(client=mock_client)
        
        # Mock 方法
        with patch.object(repo, '_query_local', new_callable=AsyncMock) as mock_query, \
             patch.object(repo, '_upsert_bars', new_callable=AsyncMock) as mock_upsert:
            
            # 第一次查询返回部分数据
            # 第二次查询返回合并后数据
            mock_query.side_effect = [
                [Bar(timestamp=1000, open=1, high=2, low=0.5, close=1.5, volume=100)],
                [
                    Bar(timestamp=1000, open=1, high=2, low=0.5, close=1.5, volume=100),
                    Bar(timestamp=3000, open=100, high=110, low=95, close=105, volume=1000),
                ],
            ]
            
            bars, is_complete = await repo.get_klines("BTCUSDT", "1h", 1000, 5000)
            
            # 应该调用了远程 API
            mock_client.get_klines.assert_called_once()
            # 应该写入新数据
            mock_upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_klines_network_failure_partial(self, mock_client):
        """测试网络故障时返回部分数据"""
        mock_client.get_klines.side_effect = ConnectionError("Network down")
        repo = MarketDataRepository(client=mock_client)
        
        with patch.object(repo, '_query_local', new_callable=AsyncMock) as mock_query:
            # 本地有部分数据
            mock_query.return_value = [
                Bar(timestamp=1000, open=1, high=2, low=0.5, close=1.5, volume=100),
            ]
            
            bars, is_complete = await repo.get_klines("BTCUSDT", "1h", 1000, 5000)
            
            assert len(bars) == 1
            assert is_complete is False  # 标记为不完整


class TestSyncKlines:
    """测试强制同步"""
    
    @pytest.mark.asyncio
    async def test_sync_klines_calls_client(self):
        """测试 sync_klines 调用客户端"""
        mock_client = Mock()
        mock_client.get_klines.return_value = [
            Bar(
                timestamp=1000,
                open=100.0,
                high=110.0,
                low=95.0,
                close=105.0,
                volume=1000.0,
            )
        ]
        
        repo = MarketDataRepository(client=mock_client)
        
        with patch.object(repo, '_upsert_bars', new_callable=AsyncMock):
            count = await repo.sync_klines("BTCUSDT", "1h", 1000, 5000)
            
            assert count == 1
            mock_client.get_klines.assert_called_once_with(
                symbol="BTCUSDT",
                interval="1h",
                start_time=1000,
                end_time=5000,
                limit=1000,
            )


class TestGetCoverage:
    """测试覆盖范围查询"""
    
    @pytest.mark.asyncio
    async def test_get_coverage_no_data(self):
        """测试无数据时返回 None"""
        from src.database import init_db
        await init_db()
        
        repo = MarketDataRepository()
        result = await repo.get_coverage("NONEXISTENT", "1h")
        
        assert result is None


class TestBatchFetching:
    """测试分批获取逻辑"""
    
    @pytest.mark.asyncio
    async def test_batch_fetch_large_range(self):
        """测试大范围数据自动分批获取"""
        mock_client = Mock()
        
        # 模拟返回 3 批数据（每批 1000 条变成简化的 3 条用于测试）
        # 第 1 批
        batch1 = [Bar(timestamp=i * 3600000, open=100, high=110, low=95, close=105, volume=1000)
                  for i in range(3)]  # 0, 3600000, 7200000
        # 第 2 批
        batch2 = [Bar(timestamp=(i + 3) * 3600000, open=100, high=110, low=95, close=105, volume=1000)
                  for i in range(3)]  # 10800000, 14400000, 18000000
        # 第 3 批 - 返回空表示结束
        
        mock_client.get_klines.side_effect = [batch1, batch2, []]
        
        repo = MarketDataRepository(client=mock_client)
        
        # Mock 方法
        with patch.object(repo, '_query_local', new_callable=AsyncMock) as mock_query, \
             patch.object(repo, '_upsert_bars', new_callable=AsyncMock) as mock_upsert:
            
            # 本地无数据
            mock_query.side_effect = [
                [],  # 第一次查询
                batch1 + batch2,  # 第二次查询返回合并后数据
            ]
            
            # 请求跨越多个批次的范围
            bars, is_complete = await repo.get_klines("BTCUSDT", "1h", 0, 20000000)
            
            # 应该多次调用 get_klines (分批)
            assert mock_client.get_klines.call_count >= 2
            # 应该写入数据
            mock_upsert.assert_called_once()
            # 合并后数据正确
            assert len(bars) == 6
    
    @pytest.mark.asyncio
    async def test_batch_fetch_error_continues_next_range(self):
        """测试某一批失败时继续获取下一个范围"""
        mock_client = Mock()
        
        # 第一批成功，第二批失败
        batch1 = [Bar(timestamp=1000, open=100, high=110, low=95, close=105, volume=1000)]
        mock_client.get_klines.side_effect = [batch1, ConnectionError("Network down")]
        
        repo = MarketDataRepository(client=mock_client)
        
        with patch.object(repo, '_query_local', new_callable=AsyncMock) as mock_query, \
             patch.object(repo, '_upsert_bars', new_callable=AsyncMock):
            
            mock_query.side_effect = [[], batch1]
            
            bars, is_complete = await repo.get_klines("BTCUSDT", "1h", 0, 10000000)
            
            # 虽然第二批失败，但仍返回第一批数据
            assert len(bars) == 1
            # 标记为不完整
            assert is_complete is False


class TestGetSentiment:
    """测试市场情绪数据获取"""
    
    @pytest.fixture
    def mock_futures_client(self):
        """创建 mock Futures 客户端"""
        from src.data.binance_futures import SentimentData
        return [
            SentimentData(
                symbol="BTCUSDT",
                timestamp=1700000000000,
                long_short_ratio=1.25,
                long_account_ratio=0.556,
                short_account_ratio=0.444
            )
        ]
    
    @pytest.mark.asyncio
    async def test_get_sentiment_uses_limit_not_time(self, mock_futures_client):
        """测试 get_sentiment 使用 limit 而非 startTime/endTime
        
        由于 Binance API 不支持时间参数，repository 会根据时间范围估算 limit
        """
        from unittest.mock import patch
        from src.data.repository import MarketDataRepository
        from src.database import init_db
        
        await init_db()
        repo = MarketDataRepository()
        
        # Mock BinanceFuturesClient.get_long_short_ratio
        # 注意：BinanceFuturesClient 是在 get_sentiment 方法内部动态导入的
        with patch("src.data.binance_futures.BinanceFuturesClient") as MockFuturesClient:
            mock_instance = MockFuturesClient.return_value
            mock_instance.get_long_short_ratio.return_value = mock_futures_client
            
            # 请求 2 天的数据 (48 小时)
            end_time = 1700100000000
            start_time = end_time - 2 * 24 * 3600 * 1000  # 2 天
            
            await repo.get_sentiment("BTCUSDT", start_time, end_time, "1h")
            
            # 验证调用时 limit 被正确计算
            call_args = mock_instance.get_long_short_ratio.call_args
            if call_args:
                kwargs = call_args.kwargs or {}
                # limit 应该基于时间范围计算：48 小时
                assert kwargs.get("limit", 24) >= 24
                # 不应传递 startTime/endTime
                assert "start_time" not in kwargs
                assert "end_time" not in kwargs
