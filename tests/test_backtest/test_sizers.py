# tests/test_backtest/test_sizers.py
"""
Sizer 模块测试

测试各种 Sizer 的计算逻辑：
- FixedSize: 固定数量
- PercentSize: 按资金百分比
- AllIn: 全仓
- RiskSize: 基于 ATR 的风险仓位
"""

import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, PropertyMock

from src.backtest.sizers import (
    BaseSizer, SizerParams,
    FixedSize, PercentSize, AllIn, RiskSize
)


@dataclass
class MockBar:
    """模拟 K 线数据"""
    open: float = 100.0
    high: float = 105.0
    low: float = 95.0
    close: float = 102.0
    volume: float = 1000.0
    timestamp: int = 1700000000000


class MockBroker:
    """模拟 Broker"""
    def __init__(self, cash: float = 10000.0):
        self._cash = cash
        self._positions = {}
    
    @property
    def cash(self) -> float:
        return self._cash
    
    @property
    def positions(self):
        return self._positions
    
    def get_position(self, symbol: str = None):
        return self._positions.get(symbol)
    
    def get_value(self, prices=None):
        return self._cash


class TestSizerParams:
    """测试 SizerParams 参数类"""
    
    def test_default_values(self):
        params = SizerParams()
        assert params.stake == 1.0
        assert params.percent == 20.0
        assert params.risk_percent == 2.0
        assert params.atr_period == 14
        assert params.atr_multiplier == 2.0
    
    def test_custom_values(self):
        params = SizerParams(stake=0.5, percent=30, risk_percent=1.5)
        assert params.stake == 0.5
        assert params.percent == 30
        assert params.risk_percent == 1.5


class TestFixedSize:
    """测试 FixedSize"""
    
    def test_returns_fixed_quantity(self):
        """固定数量 Sizer 应始终返回相同的值"""
        sizer = FixedSize(SizerParams(stake=0.5))
        bar = MockBar()
        
        assert sizer.get_size(bar, isbuy=True) == 0.5
        assert sizer.get_size(bar, isbuy=False) == 0.5
    
    def test_no_broker_required(self):
        """FixedSize 不需要 Broker"""
        sizer = FixedSize(SizerParams(stake=1.0))
        assert sizer.get_size(MockBar(), isbuy=True) == 1.0
    
    def test_default_stake(self):
        """默认 stake 为 1.0"""
        sizer = FixedSize()
        assert sizer.get_size(MockBar(), isbuy=True) == 1.0


class TestPercentSize:
    """测试 PercentSize"""
    
    def test_no_broker_returns_zero(self):
        """没有 Broker 时应返回 0"""
        sizer = PercentSize(SizerParams(percent=50))
        assert sizer.get_size(MockBar(), isbuy=True) == 0.0
    
    def test_percent_calculation(self):
        """测试百分比计算"""
        # 10000 资金，100 价格，50% 资金 = 5000 / 100 = 50 单位
        sizer = PercentSize(SizerParams(percent=50))
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        bar = MockBar(close=100)
        assert sizer.get_size(bar, isbuy=True) == 50.0
    
    def test_20_percent_calculation(self):
        """测试 20% 资金"""
        # 10000 资金，200 价格，20% 资金 = 2000 / 200 = 10 单位
        sizer = PercentSize(SizerParams(percent=20))
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        bar = MockBar(close=200)
        assert sizer.get_size(bar, isbuy=True) == 10.0
    
    def test_dict_data(self):
        """测试字典格式数据"""
        sizer = PercentSize(SizerParams(percent=50))
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        data = {'close': 100.0}
        assert sizer.get_size(data, isbuy=True) == 50.0
    
    def test_zero_price_returns_zero(self):
        """价格为 0 时应返回 0"""
        sizer = PercentSize(SizerParams(percent=50))
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        bar = MockBar(close=0)
        assert sizer.get_size(bar, isbuy=True) == 0.0


class TestAllIn:
    """测试 AllIn (全仓)"""
    
    def test_uses_full_cash(self):
        """应使用全部现金"""
        sizer = AllIn()
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        bar = MockBar(close=100)
        # 10000 / 100 = 100 单位
        assert sizer.get_size(bar, isbuy=True) == 100.0
    
    def test_no_broker_returns_zero(self):
        """没有 Broker 时应返回 0"""
        sizer = AllIn()
        assert sizer.get_size(MockBar(), isbuy=True) == 0.0
    
    def test_percent_is_100(self):
        """内部 percent 应为 100"""
        sizer = AllIn()
        assert sizer.params.percent == 100.0


class TestRiskSize:
    """测试 RiskSize (基于 ATR 的风险仓位)"""
    
    def test_no_broker_returns_zero(self):
        """没有 Broker 时应返回 0"""
        sizer = RiskSize(SizerParams(risk_percent=2))
        assert sizer.get_size(MockBar(), isbuy=True) == 0.0
    
    def test_no_strategy_returns_stake(self):
        """没有 Strategy（无 ATR）时应返回 stake"""
        sizer = RiskSize(SizerParams(stake=0.5, risk_percent=2))
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        assert sizer.get_size(MockBar(), isbuy=True) == 0.5
    
    def test_with_atr_calculation(self):
        """测试基于 ATR 的计算"""
        # 账户净值 10000，风险 2%，ATR=50，倍数=2
        # 风险金额 = 10000 * 0.02 = 200
        # 止损距离 = 50 * 2 = 100
        # 仓位 = 200 / 100 = 2
        sizer = RiskSize(SizerParams(risk_percent=2, atr_multiplier=2))
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        # 模拟策略有 atr 属性
        strategy = MagicMock()
        strategy.atr = 50.0
        sizer.set_strategy(strategy)
        
        size = sizer.get_size(MockBar(), isbuy=True)
        assert size == 2.0
    
    def test_with_atr_as_list(self):
        """测试 ATR 为列表的情况"""
        sizer = RiskSize(SizerParams(risk_percent=2, atr_multiplier=2))
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        strategy = MagicMock()
        strategy.atr = [50.0, 48.0, 52.0]  # atr[0] = 50
        sizer.set_strategy(strategy)
        
        size = sizer.get_size(MockBar(), isbuy=True)
        assert size == 2.0
    
    def test_zero_atr_returns_stake(self):
        """ATR 为 0 时应返回 stake"""
        sizer = RiskSize(SizerParams(stake=0.5, risk_percent=2))
        broker = MockBroker(cash=10000)
        sizer.set_broker(broker)
        
        strategy = MagicMock()
        strategy.atr = 0.0
        sizer.set_strategy(strategy)
        
        assert sizer.get_size(MockBar(), isbuy=True) == 0.5


class TestSizerChaining:
    """测试 Sizer 链式调用"""
    
    def test_set_broker_returns_self(self):
        sizer = PercentSize()
        result = sizer.set_broker(MockBroker())
        assert result is sizer
    
    def test_set_strategy_returns_self(self):
        sizer = RiskSize()
        result = sizer.set_strategy(MagicMock())
        assert result is sizer
    
    def test_chain_both(self):
        broker = MockBroker(cash=10000)
        strategy = MagicMock()
        strategy.atr = 50.0
        
        sizer = RiskSize(SizerParams(risk_percent=2, atr_multiplier=2))
        sizer.set_broker(broker).set_strategy(strategy)
        
        assert sizer.get_size(MockBar(), isbuy=True) == 2.0
