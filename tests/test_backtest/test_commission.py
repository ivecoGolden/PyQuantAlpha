# tests/test_backtest/test_commission.py
"""
手续费模型测试
"""

import pytest
from src.backtest.commission import CommissionScheme, CommissionManager


class TestCommissionScheme:
    """测试 CommissionScheme"""
    
    def test_default_values(self):
        scheme = CommissionScheme()
        assert scheme.maker_fee == 0.001
        assert scheme.taker_fee == 0.001
        assert scheme.min_fee == 0.0
    
    def test_custom_values(self):
        scheme = CommissionScheme(maker_fee=0.0002, taker_fee=0.0005, min_fee=1.0)
        assert scheme.maker_fee == 0.0002
        assert scheme.taker_fee == 0.0005
        assert scheme.min_fee == 1.0
    
    def test_taker_fee_calculation(self):
        """测试 Taker 费率计算"""
        scheme = CommissionScheme(taker_fee=0.001)
        # 1 BTC @ $50000 = $50000 成交额
        # 费率 0.1% = $50
        fee = scheme.calculate(size=1.0, price=50000.0, is_maker=False)
        assert fee == 50.0
    
    def test_maker_fee_calculation(self):
        """测试 Maker 费率计算"""
        scheme = CommissionScheme(maker_fee=0.0002, taker_fee=0.001)
        # Maker 0.02% of $50000 = $10
        fee = scheme.calculate(size=1.0, price=50000.0, is_maker=True)
        assert fee == 10.0
    
    def test_min_fee_applied(self):
        """测试最低手续费"""
        scheme = CommissionScheme(taker_fee=0.001, min_fee=5.0)
        # 0.01 BTC @ $100 = $1 成交额
        # 费率 0.1% = $0.001，但最低 $5
        fee = scheme.calculate(size=0.01, price=100.0)
        assert fee == 5.0
    
    def test_negative_size_absolute(self):
        """负数量应取绝对值"""
        scheme = CommissionScheme(taker_fee=0.001)
        fee_positive = scheme.calculate(size=1.0, price=100.0)
        fee_negative = scheme.calculate(size=-1.0, price=100.0)
        assert fee_positive == fee_negative


class TestCommissionManager:
    """测试 CommissionManager"""
    
    def test_default_scheme(self):
        """测试默认方案"""
        manager = CommissionManager()
        scheme = manager.get_scheme("BTCUSDT")
        assert scheme.taker_fee == 0.001
    
    def test_set_default_scheme(self):
        """测试设置默认方案"""
        manager = CommissionManager()
        manager.set_scheme(CommissionScheme(taker_fee=0.0005))
        
        scheme = manager.get_scheme("ANYUSDT")
        assert scheme.taker_fee == 0.0005
    
    def test_set_symbol_specific_scheme(self):
        """测试设置特定交易对方案"""
        manager = CommissionManager()
        manager.set_scheme(CommissionScheme(taker_fee=0.0005), symbol="BTCUSDT")
        
        # BTC 使用专属费率
        btc_scheme = manager.get_scheme("BTCUSDT")
        assert btc_scheme.taker_fee == 0.0005
        
        # 其他使用默认费率
        eth_scheme = manager.get_scheme("ETHUSDT")
        assert eth_scheme.taker_fee == 0.001
    
    def test_calculate_with_symbol(self):
        """测试按交易对计算手续费"""
        manager = CommissionManager()
        manager.set_scheme(CommissionScheme(taker_fee=0.0005), symbol="BTCUSDT")
        manager.set_scheme(CommissionScheme(taker_fee=0.001), symbol="ETHUSDT")
        
        btc_fee = manager.calculate("BTCUSDT", 1.0, 50000.0)
        eth_fee = manager.calculate("ETHUSDT", 1.0, 50000.0)
        
        assert btc_fee == 25.0   # 0.05%
        assert eth_fee == 50.0   # 0.1%
    
    def test_chain_set_scheme(self):
        """测试链式调用"""
        manager = CommissionManager()
        result = manager.set_scheme(CommissionScheme(taker_fee=0.0005))
        assert result is manager
    
    def test_reset(self):
        """测试重置"""
        manager = CommissionManager()
        manager.set_scheme(CommissionScheme(taker_fee=0.0005), symbol="BTCUSDT")
        manager.reset()
        
        scheme = manager.get_scheme("BTCUSDT")
        assert scheme.taker_fee == 0.001  # 回到默认值
