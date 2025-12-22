# tests/test_backtest/test_tf_feed.py
"""多周期对齐 Feed 测试"""

import pytest
from src.data.models import Bar
from src.backtest.feed import TimeframeAlignedFeed, create_feed

def test_tf_aligned_feed_lookahead_prevention():
    """测试多周期对齐，确保没有未来函数"""
    # 基础 1m 数据
    base_bars = [
        Bar(timestamp=i*60000, open=100, high=101, low=99, close=100.5, volume=10)
        for i in range(125) # 2h + 5m
    ]
    
    # 1h 数据
    # 1h Bar 0: ts=0, covers 0-3600000 (0-60min)
    # 1h Bar 1: ts=3600000, covers 60-120min
    h1_bars = [
        Bar(timestamp=0, open=100, high=105, low=95, close=102, volume=600),
        Bar(timestamp=3600000, open=102, high=110, low=100, close=108, volume=600),
    ]
    
    data = {
        "1m": {"BTCUSDT": base_bars},
        "1h": {"BTCUSDT": h1_bars}
    }
    
    feed = create_feed(data)
    assert isinstance(feed, TimeframeAlignedFeed)
    
    aligned_data = list(feed)
    
    # 在 ts=0 (13:00) 到 ts=3540000 (13:59) 之间，不应该看到 1h Bar 0
    # 因为 1h Bar 0 在 14:00 才结束
    for i in range(60):
        step = aligned_data[i]
        assert "1h" not in step or "BTCUSDT" not in step["1h"]
    
    # 在 ts=3600000 (14:00) 时，应该能看到 1h Bar 0 (ts=0)
    # 因为 14:00 开始的 1m Bar，13:00-14:00 的 1h Bar 已经完成了
    step_60 = aligned_data[60]
    assert "1h" in step_60
    assert step_60["1h"]["BTCUSDT"].timestamp == 0
    assert step_60["1h"]["BTCUSDT"].close == 102
    
    # 在 ts=7200000 (15:00) 时，应该能看到 1h Bar 1 (ts=3600000)
    step_120 = aligned_data[120]
    assert "1h" in step_120
    assert step_120["1h"]["BTCUSDT"].timestamp == 3600000
    assert step_120["1h"]["BTCUSDT"].close == 108

def test_tf_aligned_feed_multi_symbol():
    """测试多交易对的多周期对齐"""
    base_data = {
        "BTCUSDT": [Bar(timestamp=0, open=30000, high=30100, low=29900, close=30050, volume=10)],
        "ETHUSDT": [Bar(timestamp=0, open=2000, high=2010, low=1990, close=2005, volume=50)]
    }
    # 在 ts=0 时，无法看到任何 1h Bar。
    # 模拟一个前置 1h Bar
    h1_data = {
        "BTCUSDT": [Bar(timestamp=-3600000, open=29000, high=31000, low=28000, close=30000, volume=1000)]
    }
    
    feed = TimeframeAlignedFeed(base_data, {"1h": h1_data})
    step = next(iter(feed))
    
    assert "base" in step
    assert step["base"]["BTCUSDT"].close == 30050
    assert step["base"]["ETHUSDT"].close == 2005
    
    assert "1h" in step
    assert step["1h"]["BTCUSDT"].close == 30000
