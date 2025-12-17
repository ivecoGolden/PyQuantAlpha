# tests/test_backtest/test_feed.py
"""DataFeed 抽象测试"""

import pytest

from src.backtest.feed import DataFeed, SingleFeed, MultiFeed, create_feed
from src.data.models import Bar


def make_bars(prices: list[float], start_ts: int = 1000000) -> list[Bar]:
    """生成测试用 K 线数据"""
    return [
        Bar(
            timestamp=start_ts + i * 3600000,
            open=p,
            high=p * 1.01,
            low=p * 0.99,
            close=p,
            volume=1000.0
        )
        for i, p in enumerate(prices)
    ]


class TestSingleFeed:
    """单资产 Feed 测试"""
    
    def test_iteration(self):
        """测试遍历"""
        bars = make_bars([100, 200, 300])
        feed = SingleFeed(bars, symbol="BTCUSDT")
        
        result = list(feed)
        assert len(result) == 3
        assert result[0].close == 100
        assert result[2].close == 300
    
    def test_length(self):
        """测试长度"""
        bars = make_bars([100, 200])
        feed = SingleFeed(bars)
        assert len(feed) == 2
    
    def test_symbols(self):
        """测试交易对列表"""
        bars = make_bars([100])
        feed = SingleFeed(bars, symbol="ETHUSDT")
        assert feed.symbols == ["ETHUSDT"]
    
    def test_empty_feed(self):
        """测试空 Feed"""
        feed = SingleFeed([])
        assert len(feed) == 0
        assert list(feed) == []


class TestMultiFeed:
    """多资产 Feed 测试"""
    
    def test_basic_iteration(self):
        """测试多资产遍历"""
        btc_bars = make_bars([50000, 51000, 52000], start_ts=1000000)
        eth_bars = make_bars([3000, 3100, 3200], start_ts=1000000)
        
        btc_feed = SingleFeed(btc_bars, "BTCUSDT")
        eth_feed = SingleFeed(eth_bars, "ETHUSDT")
        
        feed = MultiFeed({"BTCUSDT": btc_feed, "ETHUSDT": eth_feed})
        
        result = list(feed)
        assert len(result) == 3
        assert result[0]["BTCUSDT"].close == 50000
        assert result[0]["ETHUSDT"].close == 3000
    
    def test_time_alignment(self):
        """测试时间对齐（并集 + Forward Fill）"""
        # BTC 有 3 个时间点 [0, 1, 2]
        btc_bars = make_bars([50000, 51000, 52000], start_ts=1000000)
        # ETH 只有 2 个时间点 [0, -, 2]（缺少第二个）
        eth_bars = [
            Bar(timestamp=1000000, open=3000, high=3030, low=2970, close=3000, volume=100),
            Bar(timestamp=1000000 + 2 * 3600000, open=3200, high=3230, low=3170, close=3200, volume=100),
        ]
        
        btc_feed = SingleFeed(btc_bars, "BTCUSDT")
        eth_feed = SingleFeed(eth_bars, "ETHUSDT")
        
        feed = MultiFeed({"BTCUSDT": btc_feed, "ETHUSDT": eth_feed})
        
        # 应该有 3 个时间点 (并集)
        result = list(feed)
        assert len(result) == 3
        
        # T0: 都有
        assert result[0]["BTCUSDT"].close == 50000
        assert result[0]["ETHUSDT"].close == 3000
        
        # T1: BTC 有, ETH 缺失 (Forward Fill 使用 T0 的值)
        assert result[1]["BTCUSDT"].close == 51000
        assert result[1]["ETHUSDT"].close == 3000  # Forward Filled
        # 即使 Forward Fill，对象本身是同一个，所以时间戳是旧的
        assert result[1]["ETHUSDT"].timestamp == 1000000 
        
        # T2: 都有
        assert result[2]["BTCUSDT"].close == 52000
        assert result[2]["ETHUSDT"].close == 3200
    
    def test_symbols(self):
        """测试交易对列表"""
        btc_feed = SingleFeed(make_bars([100]), "BTCUSDT")
        eth_feed = SingleFeed(make_bars([100]), "ETHUSDT")
        
        feed = MultiFeed({"BTCUSDT": btc_feed, "ETHUSDT": eth_feed})
        
        assert set(feed.symbols) == {"BTCUSDT", "ETHUSDT"}


class TestCreateFeed:
    """工厂函数测试"""
    
    def test_create_single_feed(self):
        """测试创建单资产 Feed"""
        bars = make_bars([100])
        feed = create_feed(bars, symbol="BTCUSDT")
        
        assert isinstance(feed, SingleFeed)
        assert feed.symbols == ["BTCUSDT"]
    
    def test_create_multi_feed(self):
        """测试创建多资产 Feed"""
        data = {
            "BTCUSDT": make_bars([50000]),
            "ETHUSDT": make_bars([3000]),
        }
        feed = create_feed(data)
        
        assert isinstance(feed, MultiFeed)
        assert set(feed.symbols) == {"BTCUSDT", "ETHUSDT"}
    
    def test_invalid_type(self):
        """测试无效类型"""
        with pytest.raises(TypeError):
            create_feed("invalid data")
