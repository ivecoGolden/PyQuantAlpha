# tests/test_data/test_bar_model.py
"""Bar 数据模型测试"""

import pytest
from dataclasses import is_dataclass

from src.data.models import Bar


class TestBarCreation:
    """测试 Bar 创建"""
    
    def test_bar_is_dataclass(self):
        """测试 Bar 是 dataclass"""
        assert is_dataclass(Bar)
    
    def test_create_with_minimal_fields(self):
        """测试最小字段创建"""
        bar = Bar(
            timestamp=1609459200000,
            open=29000.0,
            high=29500.0,
            low=28800.0,
            close=29300.0,
            volume=1000.0,
        )
        
        assert bar.timestamp == 1609459200000
        assert bar.close == 29300.0
        # 扩展字段应有默认值
        assert bar.close_time == 0
        assert bar.quote_volume == 0.0
        assert bar.trade_count == 0
    
    def test_create_with_all_fields(self):
        """测试全字段创建"""
        bar = Bar(
            timestamp=1609459200000,
            open=29000.0,
            high=29500.0,
            low=28800.0,
            close=29300.0,
            volume=1000.0,
            close_time=1609462799999,
            quote_volume=29300000.0,
            trade_count=5000,
            taker_buy_base=600.0,
            taker_buy_quote=17580000.0,
        )
        
        assert bar.close_time == 1609462799999
        assert bar.quote_volume == 29300000.0
        assert bar.trade_count == 5000
        assert bar.taker_buy_base == 600.0
        assert bar.taker_buy_quote == 17580000.0


class TestBarFields:
    """测试 Bar 字段"""
    
    @pytest.fixture
    def full_bar(self):
        """完整字段的 Bar"""
        return Bar(
            timestamp=1609459200000,
            open=29000.0,
            high=29500.0,
            low=28800.0,
            close=29300.0,
            volume=1000.0,
            close_time=1609462799999,
            quote_volume=29300000.0,
            trade_count=5000,
            taker_buy_base=600.0,
            taker_buy_quote=17580000.0,
        )
    
    def test_ohlcv_fields(self, full_bar):
        """测试 OHLCV 核心字段"""
        assert full_bar.open == 29000.0
        assert full_bar.high == 29500.0
        assert full_bar.low == 28800.0
        assert full_bar.close == 29300.0
        assert full_bar.volume == 1000.0
    
    def test_extended_fields(self, full_bar):
        """测试扩展字段"""
        assert full_bar.close_time == 1609462799999
        assert full_bar.quote_volume == 29300000.0
        assert full_bar.trade_count == 5000
        assert full_bar.taker_buy_base == 600.0
        assert full_bar.taker_buy_quote == 17580000.0


class TestBarToDict:
    """测试 Bar 转字典"""
    
    @pytest.fixture
    def bar(self):
        return Bar(
            timestamp=1609459200000,
            open=29000.0,
            high=29500.0,
            low=28800.0,
            close=29300.0,
            volume=1000.0,
            close_time=1609462799999,
            quote_volume=29300000.0,
            trade_count=5000,
            taker_buy_base=600.0,
            taker_buy_quote=17580000.0,
        )
    
    def test_to_dict_all_fields(self, bar):
        """测试 to_dict 包含所有字段"""
        result = bar.to_dict()
        
        assert isinstance(result, dict)
        assert len(result) == 11
        assert result["timestamp"] == 1609459200000
        assert result["close"] == 29300.0
        assert result["close_time"] == 1609462799999
        assert result["quote_volume"] == 29300000.0
        assert result["trade_count"] == 5000
        assert result["taker_buy_base"] == 600.0
        assert result["taker_buy_quote"] == 17580000.0
    
    def test_to_basic_dict_core_fields(self, bar):
        """测试 to_basic_dict 仅包含核心字段"""
        result = bar.to_basic_dict()
        
        assert isinstance(result, dict)
        assert len(result) == 6
        assert "timestamp" in result
        assert "open" in result
        assert "high" in result
        assert "low" in result
        assert "close" in result
        assert "volume" in result
        # 不应包含扩展字段
        assert "close_time" not in result
        assert "quote_volume" not in result
        assert "trade_count" not in result


class TestBarDefaultValues:
    """测试 Bar 默认值"""
    
    def test_extended_fields_default_to_zero(self):
        """测试扩展字段默认值为零"""
        bar = Bar(
            timestamp=1000,
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=500.0,
        )
        
        assert bar.close_time == 0
        assert bar.quote_volume == 0.0
        assert bar.trade_count == 0
        assert bar.taker_buy_base == 0.0
        assert bar.taker_buy_quote == 0.0
    
    def test_backward_compatibility(self):
        """测试向后兼容性 - 旧代码只用 6 字段"""
        # 模拟旧代码创建方式
        bar = Bar(
            timestamp=1000,
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=500.0,
        )
        
        # 老代码仍然可以正常访问核心字段
        assert bar.open == 100.0
        assert bar.close == 105.0
        
        # 老代码调用 to_basic_dict 不会出错
        basic = bar.to_basic_dict()
        assert basic["close"] == 105.0


class TestBarEquality:
    """测试 Bar 相等性"""
    
    def test_same_values_are_equal(self):
        """测试相同值相等"""
        bar1 = Bar(timestamp=1000, open=100, high=110, low=90, close=105, volume=500)
        bar2 = Bar(timestamp=1000, open=100, high=110, low=90, close=105, volume=500)
        
        assert bar1 == bar2
    
    def test_different_values_not_equal(self):
        """测试不同值不相等"""
        bar1 = Bar(timestamp=1000, open=100, high=110, low=90, close=105, volume=500)
        bar2 = Bar(timestamp=2000, open=100, high=110, low=90, close=105, volume=500)
        
        assert bar1 != bar2
