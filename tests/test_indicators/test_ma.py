# tests/test_indicators/test_ma.py
"""移动平均指标测试"""

import pytest

from src.indicators import SMA, EMA


class TestSMA:
    """SMA 指标测试"""
    
    def test_sma_basic(self):
        """测试 SMA 基本计算"""
        sma = SMA(5)
        prices = [10, 11, 12, 13, 14]
        
        results = []
        for p in prices:
            result = sma.update(p)
            results.append(result)
        
        # 前 4 个应该返回 None
        assert results[:4] == [None, None, None, None]
        # 第 5 个应该返回平均值
        assert results[4] == 12.0  # (10+11+12+13+14)/5
    
    def test_sma_sliding_window(self):
        """测试 SMA 滑动窗口"""
        sma = SMA(3)
        
        sma.update(10)
        sma.update(20)
        result1 = sma.update(30)  # (10+20+30)/3 = 20
        result2 = sma.update(40)  # (20+30+40)/3 = 30
        
        assert result1 == 20.0
        assert result2 == 30.0
    
    def test_sma_reset(self):
        """测试 SMA 重置"""
        sma = SMA(2)
        sma.update(10)
        sma.update(20)
        
        assert sma.value == 15.0
        
        sma.reset()
        assert sma.value is None
        assert sma.ready is False
    
    def test_sma_invalid_period(self):
        """测试无效周期"""
        with pytest.raises(ValueError):
            SMA(0)
        
        with pytest.raises(ValueError):
            SMA(-1)


class TestEMA:
    """EMA 指标测试"""
    
    def test_ema_basic(self):
        """测试 EMA 基本计算"""
        ema = EMA(5)
        prices = [10, 11, 12, 13, 14]
        
        results = []
        for p in prices:
            result = ema.update(p)
            results.append(result)
        
        # 前 4 个应该返回 None（数据不足周期）
        assert results[:4] == [None, None, None, None]
        # 第 5 个应该返回 EMA 值
        assert results[4] is not None
    
    def test_ema_responsive_to_price(self):
        """测试 EMA 对价格响应"""
        ema = EMA(3)
        
        # 先填充数据
        for _ in range(3):
            ema.update(100)
        
        # 价格跳升
        result1 = ema.value
        ema.update(200)
        result2 = ema.value
        
        # EMA 应该上升但不会直接跳到 200
        assert result2 > result1
        assert result2 < 200
    
    def test_ema_alpha(self):
        """测试 EMA alpha 计算"""
        ema = EMA(10)
        expected_alpha = 2.0 / (10 + 1)
        assert ema._alpha == expected_alpha
    
    def test_ema_reset(self):
        """测试 EMA 重置"""
        ema = EMA(3)
        for p in [10, 20, 30]:
            ema.update(p)
        
        assert ema.ready is True
        
        ema.reset()
        assert ema.ready is False
        assert ema._count == 0
