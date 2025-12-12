# tests/test_indicators/test_volatility.py
"""波动率指标测试"""

import pytest

from src.indicators import ATR, BollingerBands


class TestATR:
    """ATR 指标测试"""
    
    def test_atr_basic(self):
        """测试 ATR 基本计算"""
        atr = ATR(14)
        
        # 模拟 OHLC 数据
        bars = [
            (48.70, 47.79, 48.16),
            (48.72, 48.14, 48.61),
            (48.90, 48.39, 48.75),
            (48.87, 48.37, 48.63),
            (48.82, 48.24, 48.74),
            (49.05, 48.64, 49.03),
            (49.20, 48.94, 49.07),
            (49.35, 48.86, 49.32),
            (49.92, 49.50, 49.91),
            (50.19, 49.87, 50.13),
            (50.12, 49.20, 49.53),
            (49.66, 48.90, 49.50),
            (49.88, 49.43, 49.75),
            (50.19, 49.73, 50.03),
            (50.36, 49.26, 50.31),
        ]
        
        results = []
        for high, low, close in bars:
            result = atr.update(high, low, close)
            results.append(result)
        
        # 前 N-1 个应该返回 None
        assert all(r is None for r in results[:13])
        # 第 14 个应该返回 ATR 值
        assert results[13] is not None
        assert results[13] > 0
    
    def test_atr_volatility_increase(self):
        """测试 ATR 对波动率增加的响应"""
        atr = ATR(5)
        
        # 低波动
        for _ in range(5):
            atr.update(100, 99, 99.5)
        
        low_vol = atr.value
        
        # 高波动
        for _ in range(5):
            atr.update(110, 90, 100)
        
        high_vol = atr.value
        
        assert high_vol > low_vol
    
    def test_atr_reset(self):
        """测试 ATR 重置"""
        atr = ATR(3)
        
        for _ in range(5):
            atr.update(100, 95, 98)
        
        assert atr.ready is True
        
        atr.reset()
        assert atr.ready is False
        assert atr._prev_close is None


class TestBollingerBands:
    """布林带指标测试"""
    
    def test_bb_basic(self):
        """测试布林带基本计算"""
        bb = BollingerBands(20, 2)
        
        # 模拟价格数据
        for i in range(25):
            result = bb.update(100 + i % 5)
        
        assert result is not None
        assert hasattr(result, 'upper')
        assert hasattr(result, 'middle')
        assert hasattr(result, 'lower')
    
    def test_bb_structure(self):
        """测试布林带结构"""
        bb = BollingerBands(5, 2)
        
        for i in range(10):
            result = bb.update(100 + i)
        
        # 上轨 > 中轨 > 下轨
        assert result.upper > result.middle > result.lower
    
    def test_bb_flat_prices(self):
        """测试价格平稳时的布林带"""
        bb = BollingerBands(5, 2)
        
        # 价格完全平稳
        for _ in range(10):
            result = bb.update(100)
        
        # 标准差为 0，上下轨等于中轨
        assert result.upper == result.middle == result.lower == 100
    
    def test_bb_volatility(self):
        """测试波动率对布林带的影响"""
        bb1 = BollingerBands(5, 2)
        bb2 = BollingerBands(5, 2)
        
        # 低波动
        for p in [100, 101, 99, 100, 101]:
            bb1.update(p)
        
        # 高波动
        for p in [100, 120, 80, 110, 90]:
            bb2.update(p)
        
        # 高波动带宽更大
        width1 = bb1.bands.upper - bb1.bands.lower
        width2 = bb2.bands.upper - bb2.bands.lower
        
        assert width2 > width1
    
    def test_bb_reset(self):
        """测试布林带重置"""
        bb = BollingerBands(3, 2)
        
        for p in [100, 101, 102, 103]:
            bb.update(p)
        
        assert bb.ready is True
        
        bb.reset()
        assert bb.ready is False
        assert bb.bands is None
