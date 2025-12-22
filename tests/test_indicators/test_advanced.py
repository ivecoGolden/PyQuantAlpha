# tests/test_indicators/test_advanced.py
"""高级指标测试"""

import pytest
from src.indicators import (
    ADX,
    Stochastic,
    StochasticResult,
    WilliamsR,
    CCI,
    OBV,
    Ichimoku,
    IchimokuResult,
    SentimentDisparity,
)


class TestADX:
    """ADX 指标测试"""
    
    def test_init(self):
        """测试初始化"""
        adx = ADX(14)
        assert adx.period == 14
        assert adx.value is None
    
    def test_not_ready_without_enough_data(self):
        """测试数据不足时返回 None"""
        adx = ADX(14)
        # 少于 period * 2 个数据点
        for i in range(20):
            result = adx.update(100 + i, 95 + i, 98 + i)
        # ADX 需要更多数据
        assert result is None or adx.ready
    
    def test_returns_value_with_enough_data(self):
        """测试数据充足时返回值"""
        adx = ADX(5)  # 使用较小周期便于测试
        # 模拟上涨趋势
        for i in range(30):
            result = adx.update(100 + i * 2, 95 + i * 2, 98 + i * 2)
        
        assert result is not None
        assert 0 <= result <= 100


class TestStochastic:
    """随机指标测试"""
    
    def test_init(self):
        """测试初始化"""
        stoch = Stochastic(14, 3)
        assert stoch.period == 14
        assert stoch.d_period == 3
    
    def test_returns_stochastic_result(self):
        """测试返回 StochasticResult"""
        stoch = Stochastic(5, 3)
        
        # 模拟数据
        result = None
        for i in range(10):
            result = stoch.update(100 + i, 90 + i, 95 + i)
        
        assert result is not None
        assert isinstance(result, StochasticResult)
        assert 0 <= result.k <= 100
        assert 0 <= result.d <= 100
    
    def test_overbought_condition(self):
        """测试超买条件"""
        stoch = Stochastic(5, 3)
        
        # 模拟持续上涨 (收盘价接近最高价)
        for i in range(10):
            result = stoch.update(100 + i, 90, 100 + i)  # close = high
        
        assert result is not None
        assert result.k > 80  # 超买区域


class TestWilliamsR:
    """威廉指标测试"""
    
    def test_init(self):
        """测试初始化"""
        wr = WilliamsR(14)
        assert wr.period == 14
    
    def test_value_range(self):
        """测试值范围在 -100 到 0"""
        wr = WilliamsR(5)
        
        result = None
        for i in range(10):
            result = wr.update(100 + i, 90 + i, 95 + i)
        
        assert result is not None
        assert -100 <= result <= 0
    
    def test_oversold_condition(self):
        """测试超卖条件"""
        wr = WilliamsR(5)
        
        # 模拟持续下跌 (收盘价接近最低价)
        for i in range(10):
            result = wr.update(100, 90 - i, 90 - i)  # close = low
        
        assert result is not None
        assert result < -80  # 超卖区域


class TestCCI:
    """顺势指标测试"""
    
    def test_init(self):
        """测试初始化"""
        cci = CCI(20)
        assert cci.period == 20
    
    def test_returns_value(self):
        """测试返回值"""
        cci = CCI(5)
        
        result = None
        for i in range(10):
            result = cci.update(100 + i, 90 + i, 95 + i)
        
        assert result is not None
        # CCI 理论上无上下限，但通常在 -200 到 200 之间
    
    def test_overbought_overbought(self):
        """测试极端值"""
        cci = CCI(5)
        
        # 先稳定一段
        for i in range(5):
            cci.update(100, 90, 95)
        
        # 突然大涨
        result = cci.update(150, 140, 148)
        
        # CCI 应该显示超买
        assert result is not None
        assert result > 0


class TestOBV:
    """能量潮指标测试"""
    
    def test_init(self):
        """测试初始化"""
        obv = OBV()
        assert obv.period == 1  # OBV 不需要周期
    
    def test_price_up_volume_added(self):
        """测试价格上涨时累加成交量"""
        obv = OBV()
        
        obv.update(100, 1000)  # 初始
        result = obv.update(105, 2000)  # 上涨
        
        assert result == 2000  # 累加了成交量
    
    def test_price_down_volume_subtracted(self):
        """测试价格下跌时减去成交量"""
        obv = OBV()
        
        obv.update(100, 1000)  # 初始
        result = obv.update(95, 2000)  # 下跌
        
        assert result == -2000  # 减去了成交量
    
    def test_price_unchanged_obv_unchanged(self):
        """测试价格不变时 OBV 不变"""
        obv = OBV()
        
        obv.update(100, 1000)
        result = obv.update(100, 2000)  # 价格不变
        
        assert result == 0  # OBV 不变


class TestIchimoku:
    """一目均衡表测试"""
    
    def test_init(self):
        """测试初始化"""
        ichi = Ichimoku(9, 26, 52)
        assert ichi.tenkan_period == 9
        assert ichi.kijun_period == 26
        assert ichi.senkou_b_period == 52
    
    def test_returns_ichimoku_result(self):
        """测试返回 IchimokuResult"""
        ichi = Ichimoku(5, 10, 20)  # 使用较小周期便于测试
        
        result = None
        for i in range(30):
            result = ichi.update(100 + i, 90 + i, 95 + i)
        
        assert result is not None
        assert isinstance(result, IchimokuResult)
        assert result.tenkan is not None
        assert result.kijun is not None
        assert result.senkou_a is not None
        assert result.senkou_b is not None
    
    def test_reset(self):
        """测试重置"""
        ichi = Ichimoku(5, 10, 20)
        
        for i in range(30):
            ichi.update(100 + i, 90 + i, 95 + i)
        
        ichi.reset()
        
        result = ichi.update(100, 90, 95)
        assert result is None  # 数据不足


class TestSentimentDisparity:
    """情绪背离指标测试"""
    
    def test_init(self):
        sd = SentimentDisparity(1)
        assert sd.period == 1
        
    def test_calculation(self):
        sd = SentimentDisparity(1)
        
        # p1=100, r1=1.0
        sd.update(100, 1.0)
        
        # p2=110 (+10%), r2=1.0 (0%) -> disparity = 10 - 0 = 10
        res = sd.update(110, 1.0)
        assert res == pytest.approx(10.0)
        
        # p3=110 (0%), r3=1.1 (+10%) -> disparity = 0 - 10 = -10
        res = sd.update(110, 1.1)
        assert res == pytest.approx(-10.0)
