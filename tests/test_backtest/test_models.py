# tests/test_backtest/test_models.py
"""回测数据模型测试"""

import pytest

from src.backtest.models import (
    OrderSide,
    OrderStatus,
    OrderType,
    Order,
    Trade,
    Position,
    BacktestConfig,
    BacktestResult,
)


class TestOrderSide:
    """OrderSide 枚举测试"""
    
    def test_buy_value(self):
        assert OrderSide.BUY.value == "BUY"
    
    def test_sell_value(self):
        assert OrderSide.SELL.value == "SELL"


class TestOrderStatus:
    """OrderStatus 枚举测试"""
    
    def test_all_statuses(self):
        assert OrderStatus.PENDING.value == "PENDING"
        assert OrderStatus.FILLED.value == "FILLED"
        assert OrderStatus.CANCELLED.value == "CANCELLED"
        assert OrderStatus.REJECTED.value == "REJECTED"


class TestOrder:
    """Order 数据类测试"""
    
    def test_create_market_order(self):
        order = Order(
            id="O001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        assert order.id == "O001"
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.quantity == 0.1
        assert order.status == OrderStatus.PENDING
        assert order.price is None
    
    def test_create_limit_order(self):
        order = Order(
            id="O002",
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=2000.0
        )
        
        assert order.order_type == OrderType.LIMIT
        assert order.price == 2000.0


class TestPosition:
    """Position 数据类测试"""
    
    def test_create_empty_position(self):
        pos = Position(symbol="BTCUSDT")
        
        assert pos.symbol == "BTCUSDT"
        assert pos.quantity == 0.0
        assert pos.avg_price == 0.0
    
    def test_new_long_position(self):
        """测试新开多头"""
        pos = Position(symbol="BTCUSDT")
        pnl = pos.update(1.0, 50000.0)
        
        assert pos.quantity == 1.0
        assert pos.avg_price == 50000.0
        assert pnl == 0.0  # 开仓无盈亏
    
    def test_add_to_long_position(self):
        """测试多头加仓"""
        pos = Position(symbol="BTCUSDT")
        pos.update(1.0, 50000.0)
        pos.update(1.0, 52000.0)
        
        assert pos.quantity == 2.0
        # 均价 = (50000 + 52000) / 2 = 51000
        assert pos.avg_price == 51000.0
    
    def test_close_long_position_profit(self):
        """测试多头平仓盈利"""
        pos = Position(symbol="BTCUSDT")
        pos.update(1.0, 50000.0)  # 开仓
        pnl = pos.update(-1.0, 55000.0)  # 平仓
        
        assert pos.quantity == 0.0
        assert pos.avg_price == 0.0
        assert pnl == 5000.0  # 盈利 5000
    
    def test_close_long_position_loss(self):
        """测试多头平仓亏损"""
        pos = Position(symbol="BTCUSDT")
        pos.update(1.0, 50000.0)
        pnl = pos.update(-1.0, 48000.0)
        
        assert pnl == -2000.0  # 亏损 2000
    
    def test_partial_close(self):
        """测试部分平仓"""
        pos = Position(symbol="BTCUSDT")
        pos.update(2.0, 50000.0)
        pnl = pos.update(-1.0, 55000.0)  # 平一半
        
        assert pos.quantity == 1.0
        assert pos.avg_price == 50000.0  # 均价不变
        assert pnl == 5000.0
    
    def test_unrealized_pnl(self):
        """测试未实现盈亏"""
        pos = Position(symbol="BTCUSDT")
        pos.update(1.0, 50000.0)
        
        pnl = pos.unrealized_pnl(55000.0)
        assert pnl == 5000.0
        
        pnl = pos.unrealized_pnl(45000.0)
        assert pnl == -5000.0
    
    def test_market_value(self):
        """测试市值计算"""
        pos = Position(symbol="BTCUSDT")
        pos.update(2.0, 50000.0)
        
        mv = pos.market_value(55000.0)
        assert mv == 110000.0


class TestBacktestConfig:
    """BacktestConfig 默认值测试"""
    
    def test_default_values(self):
        config = BacktestConfig()
        
        assert config.initial_capital == 100000.0
        assert config.commission_rate == 0.001
        assert config.slippage == 0.0005
    
    def test_custom_values(self):
        config = BacktestConfig(
            initial_capital=50000.0,
            commission_rate=0.0005,
            slippage=0.001
        )
        
        assert config.initial_capital == 50000.0
        assert config.commission_rate == 0.0005
