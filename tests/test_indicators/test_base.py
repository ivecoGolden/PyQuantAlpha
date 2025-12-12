# tests/test_indicators/test_base.py
"""指标基类测试"""

import pytest
from dataclasses import is_dataclass

from src.indicators.base import BaseIndicator, MACDResult, BollingerResult


class TestMACDResult:
    """MACDResult 数据类测试"""
    
    def test_is_dataclass(self):
        """测试是 dataclass"""
        assert is_dataclass(MACDResult)
    
    def test_macd_result_creation(self):
        """测试 MACDResult 创建"""
        result = MACDResult(macd_line=1.5, signal_line=1.0, histogram=0.5)
        
        assert result.macd_line == 1.5
        assert result.signal_line == 1.0
        assert result.histogram == 0.5
    
    def test_macd_result_equality(self):
        """测试 MACDResult 相等性"""
        r1 = MACDResult(macd_line=1.0, signal_line=0.8, histogram=0.2)
        r2 = MACDResult(macd_line=1.0, signal_line=0.8, histogram=0.2)
        
        assert r1 == r2
    
    def test_macd_result_fields(self):
        """测试 MACDResult 字段"""
        result = MACDResult(macd_line=0, signal_line=0, histogram=0)
        
        assert hasattr(result, 'macd_line')
        assert hasattr(result, 'signal_line')
        assert hasattr(result, 'histogram')


class TestBollingerResult:
    """BollingerResult 数据类测试"""
    
    def test_is_dataclass(self):
        """测试是 dataclass"""
        assert is_dataclass(BollingerResult)
    
    def test_bollinger_result_creation(self):
        """测试 BollingerResult 创建"""
        result = BollingerResult(upper=110.0, middle=100.0, lower=90.0)
        
        assert result.upper == 110.0
        assert result.middle == 100.0
        assert result.lower == 90.0
    
    def test_bollinger_result_equality(self):
        """测试 BollingerResult 相等性"""
        r1 = BollingerResult(upper=120, middle=100, lower=80)
        r2 = BollingerResult(upper=120, middle=100, lower=80)
        
        assert r1 == r2
    
    def test_bollinger_result_fields(self):
        """测试 BollingerResult 字段"""
        result = BollingerResult(upper=0, middle=0, lower=0)
        
        assert hasattr(result, 'upper')
        assert hasattr(result, 'middle')
        assert hasattr(result, 'lower')


class TestBaseIndicator:
    """BaseIndicator 抽象基类测试"""
    
    def test_cannot_instantiate_directly(self):
        """测试不能直接实例化"""
        with pytest.raises(TypeError):
            BaseIndicator(14)
    
    def test_invalid_period_zero(self):
        """测试无效周期 0"""
        # 创建一个具体实现来测试
        class ConcreteIndicator(BaseIndicator):
            def update(self, value):
                return None
        
        with pytest.raises(ValueError) as exc_info:
            ConcreteIndicator(0)
        
        assert "周期必须" in str(exc_info.value)
    
    def test_invalid_period_negative(self):
        """测试无效周期负数"""
        class ConcreteIndicator(BaseIndicator):
            def update(self, value):
                return None
        
        with pytest.raises(ValueError):
            ConcreteIndicator(-5)
    
    def test_valid_period(self):
        """测试有效周期"""
        class ConcreteIndicator(BaseIndicator):
            def update(self, value):
                return None
        
        indicator = ConcreteIndicator(14)
        assert indicator.period == 14
    
    def test_initial_value_is_none(self):
        """测试初始值为 None"""
        class ConcreteIndicator(BaseIndicator):
            def update(self, value):
                return None
        
        indicator = ConcreteIndicator(10)
        assert indicator.value is None
    
    def test_initial_ready_is_false(self):
        """测试初始 ready 为 False"""
        class ConcreteIndicator(BaseIndicator):
            def update(self, value):
                return None
        
        indicator = ConcreteIndicator(10)
        assert indicator.ready is False
    
    def test_reset_clears_values(self):
        """测试 reset 清空数据"""
        class ConcreteIndicator(BaseIndicator):
            def update(self, value):
                self._values.append(value)
                if len(self._values) >= self.period:
                    self._result = sum(self._values[-self.period:]) / self.period
                return self._result
        
        indicator = ConcreteIndicator(3)
        for v in [10, 20, 30]:
            indicator.update(v)
        
        assert indicator.ready is True
        
        indicator.reset()
        assert indicator.ready is False
        assert indicator.value is None
        assert len(indicator._values) == 0
    
    def test_repr(self):
        """测试 __repr__ 方法"""
        class ConcreteIndicator(BaseIndicator):
            def update(self, value):
                return None
        
        indicator = ConcreteIndicator(20)
        repr_str = repr(indicator)
        
        assert "ConcreteIndicator" in repr_str
        assert "period=20" in repr_str
