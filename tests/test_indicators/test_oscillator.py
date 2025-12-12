# tests/test_indicators/test_oscillator.py
"""振荡器指标测试"""

import pytest

from src.indicators import RSI, MACD


class TestRSI:
    """RSI 指标测试"""
    
    def test_rsi_basic(self):
        """测试 RSI 基本计算"""
        rsi = RSI(14)
        
        # 模拟价格数据
        prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10,
                  45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
        
        results = []
        for p in prices:
            result = rsi.update(p)
            results.append(result)
        
        # 前 N 个应该返回 None
        assert all(r is None for r in results[:13])
        # 第 15 个应该返回 RSI 值
        assert results[14] is not None
        assert 0 <= results[14] <= 100
    
    def test_rsi_overbought(self):
        """测试 RSI 超买区域"""
        rsi = RSI(5)
        
        # 连续上涨
        for i in range(10):
            rsi.update(100 + i * 10)
        
        # RSI 应该接近 100
        assert rsi.value > 70
    
    def test_rsi_oversold(self):
        """测试 RSI 超卖区域"""
        rsi = RSI(5)
        
        # 连续下跌
        for i in range(10):
            rsi.update(100 - i * 10)
        
        # RSI 应该接近 0
        assert rsi.value < 30
    
    def test_rsi_range(self):
        """测试 RSI 值域"""
        rsi = RSI(7)
        
        # 混合波动
        prices = [100, 105, 103, 108, 102, 110, 95, 115, 90, 120]
        for p in prices:
            result = rsi.update(p)
            if result is not None:
                assert 0 <= result <= 100


class TestMACD:
    """MACD 指标测试"""
    
    def test_macd_basic(self):
        """测试 MACD 基本计算"""
        macd = MACD(12, 26, 9)
        
        # 需要足够数据
        for i in range(40):
            result = macd.update(100 + i)
        
        assert result is not None
        assert hasattr(result, 'macd_line')
        assert hasattr(result, 'signal_line')
        assert hasattr(result, 'histogram')
    
    def test_macd_structure(self):
        """测试 MACD 结果结构"""
        macd = MACD(3, 5, 2)
        
        # 快速周期
        for i in range(10):
            result = macd.update(100 + i)
        
        assert result.macd_line == result.macd_line  # not NaN
        assert result.histogram == result.macd_line - result.signal_line
    
    def test_macd_trend(self):
        """测试 MACD 趋势识别"""
        macd = MACD(3, 5, 2)
        
        # 上升趋势
        for i in range(15):
            macd.update(100 + i * 2)
        
        result = macd.macd_value
        # 上升趋势中，MACD 线应该为正
        assert result.macd_line > 0
    
    def test_macd_reset(self):
        """测试 MACD 重置"""
        macd = MACD(3, 5, 2)
        
        for i in range(10):
            macd.update(100 + i)
        
        assert macd.ready is True
        
        macd.reset()
        assert macd.ready is False
        assert macd.macd_value is None
