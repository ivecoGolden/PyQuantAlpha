# tests/test_data/test_resampler.py
"""Resampler 单元测试"""

import pytest
from src.data.models import Bar
from src.data.resampler import Resampler

def test_resample_basic_1m_to_5m():
    """测试 1m 聚合到 5m (OHLCV)"""
    bars = [
        Bar(timestamp=0, open=10, high=12, low=9, close=11, volume=100),
        Bar(timestamp=60000, open=11, high=13, low=11, close=12, volume=100),
        Bar(timestamp=120000, open=12, high=14, low=10, close=10, volume=100),
        Bar(timestamp=180000, open=10, high=11, low=9, close=10, volume=100),
        Bar(timestamp=240000, open=10, high=15, low=10, close=14, volume=100),
        # 下一个桶
        Bar(timestamp=300000, open=14, high=16, low=14, close=15, volume=100),
    ]
    
    resampled = Resampler.resample(bars, "5m")
    
    assert len(resampled) == 2
    
    # 桶 1 (0-240000)
    b1 = resampled[0]
    assert b1.timestamp == 0
    assert b1.open == 10
    assert b1.high == 15
    assert b1.low == 9
    assert b1.close == 14
    assert b1.volume == 500
    assert b1.close_time == 5 * 60 * 1000 - 1
    
    # 桶 2 (300000)
    b2 = resampled[1]
    assert b2.timestamp == 300000
    assert b2.open == 14
    assert b2.high == 16
    assert b2.low == 14
    assert b2.close == 15
    assert b2.volume == 100

def test_resample_extended_fields():
    """测试扩展字段聚合"""
    bars = [
        Bar(timestamp=0, open=10, high=11, low=9, close=10, volume=100, 
            quote_volume=1000, trade_count=10, taker_buy_base=50, taker_buy_quote=500),
        Bar(timestamp=60000, open=10, high=12, low=10, close=11, volume=200, 
            quote_volume=2200, trade_count=20, taker_buy_base=120, taker_buy_quote=1300),
    ]
    
    resampled = Resampler.resample(bars, "5m")
    assert len(resampled) == 1
    b = resampled[0]
    assert b.volume == 300
    assert b.quote_volume == 3200
    assert b.trade_count == 30
    assert b.taker_buy_base == 170
    assert b.taker_buy_quote == 1800

def test_resample_empty_input():
    """测试空输入"""
    assert Resampler.resample([], "1h") == []

def test_resample_invalid_interval():
    """测试无效频率"""
    with pytest.raises(ValueError, match="无效的目标周期"):
        Resampler.resample([Bar(0,1,1,1,1,1)], "99m")

def test_resample_unaligned_start():
    """测试非整点对齐的开始时间"""
    # 如果 1m 数据从 13:02 开始，聚合 5m，第一个桶应该是 13:00 - 13:05
    # timestamp=120000 (2min)
    bars = [
        Bar(timestamp=120000, open=10, high=15, low=8, close=12, volume=100),
        Bar(timestamp=180000, open=12, high=13, low=11, close=11, volume=100),
    ]
    resampled = Resampler.resample(bars, "5m")
    assert len(resampled) == 1
    assert resampled[0].timestamp == 0
    assert resampled[0].open == 10
    assert resampled[0].high == 15
    assert resampled[0].low == 8
    assert resampled[0].close == 11
