# tests/test_backtest/test_slippage.py
"""
滑点模型测试
"""

import pytest
from src.backtest.slippage import (
    BaseSlippage, SlippageParams,
    FixedSlippage, PercentSlippage, VolumeSlippage
)


class TestSlippageParams:
    """测试 SlippageParams"""
    
    def test_default_values(self):
        params = SlippageParams()
        assert params.fixed_amount == 0.0
        assert params.percent == 0.0
        assert params.volume_impact == 0.1
    
    def test_custom_values(self):
        params = SlippageParams(fixed_amount=0.5, percent=0.001)
        assert params.fixed_amount == 0.5
        assert params.percent == 0.001


class TestFixedSlippage:
    """测试 FixedSlippage"""
    
    def test_buy_increases_price(self):
        """买入时滑点应增加成交价格"""
        slippage = FixedSlippage(SlippageParams(fixed_amount=0.5))
        result = slippage.calculate(100.0, 1.0, is_buy=True)
        assert result == 100.5
    
    def test_sell_decreases_price(self):
        """卖出时滑点应减少成交价格"""
        slippage = FixedSlippage(SlippageParams(fixed_amount=0.5))
        result = slippage.calculate(100.0, 1.0, is_buy=False)
        assert result == 99.5
    
    def test_zero_slippage(self):
        """零滑点"""
        slippage = FixedSlippage(SlippageParams(fixed_amount=0.0))
        assert slippage.calculate(100.0, 1.0, is_buy=True) == 100.0
        assert slippage.calculate(100.0, 1.0, is_buy=False) == 100.0


class TestPercentSlippage:
    """测试 PercentSlippage"""
    
    def test_buy_increases_price(self):
        """买入时百分比滑点增加价格"""
        # 0.1% 滑点
        slippage = PercentSlippage(SlippageParams(percent=0.001))
        result = slippage.calculate(1000.0, 1.0, is_buy=True)
        assert result == 1001.0  # 1000 * 1.001
    
    def test_sell_decreases_price(self):
        """卖出时百分比滑点减少价格"""
        slippage = PercentSlippage(SlippageParams(percent=0.001))
        result = slippage.calculate(1000.0, 1.0, is_buy=False)
        assert result == 999.0  # 1000 * 0.999
    
    def test_one_percent_slippage(self):
        """1% 滑点"""
        slippage = PercentSlippage(SlippageParams(percent=0.01))
        assert slippage.calculate(100.0, 1.0, is_buy=True) == 101.0
        assert slippage.calculate(100.0, 1.0, is_buy=False) == 99.0


class TestVolumeSlippage:
    """测试 VolumeSlippage"""
    
    def test_no_market_volume_returns_original(self):
        """没有市场成交量时返回原价"""
        slippage = VolumeSlippage(SlippageParams(volume_impact=0.1))
        result = slippage.calculate(100.0, 10.0, is_buy=True, market_volume=None)
        assert result == 100.0
    
    def test_zero_market_volume_returns_original(self):
        """市场成交量为 0 时返回原价"""
        slippage = VolumeSlippage(SlippageParams(volume_impact=0.1))
        result = slippage.calculate(100.0, 10.0, is_buy=True, market_volume=0)
        assert result == 100.0
    
    def test_volume_impact_calculation(self):
        """测试成交量影响计算"""
        # 订单量 10，市场量 100，冲击系数 0.1
        # 冲击比例 = 10/100 = 0.1
        # 滑点 = 100 * 0.1 * 0.1 = 1
        slippage = VolumeSlippage(SlippageParams(volume_impact=0.1))
        result = slippage.calculate(100.0, 10.0, is_buy=True, market_volume=100.0)
        assert result == 101.0
    
    def test_large_order_more_slippage(self):
        """大订单应有更大滑点"""
        slippage = VolumeSlippage(SlippageParams(volume_impact=0.1))
        
        small_order = slippage.calculate(100.0, 10.0, is_buy=True, market_volume=100.0)
        large_order = slippage.calculate(100.0, 50.0, is_buy=True, market_volume=100.0)
        
        assert large_order > small_order


class TestSlippageRepr:
    """测试 __repr__"""
    
    def test_fixed_slippage_repr(self):
        slippage = FixedSlippage(SlippageParams(fixed_amount=0.5))
        assert "FixedSlippage" in repr(slippage)
    
    def test_percent_slippage_repr(self):
        slippage = PercentSlippage(SlippageParams(percent=0.001))
        assert "PercentSlippage" in repr(slippage)
