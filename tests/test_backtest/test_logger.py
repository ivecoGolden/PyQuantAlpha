# tests/test_backtest/test_logger.py
"""回测日志系统测试"""

import pytest
from src.backtest.logger import BacktestLogger
from src.backtest.models import Order, OrderSide, OrderType, OrderStatus
from src.data.models import Bar


class TestBacktestLogger:
    """BacktestLogger 测试"""
    
    def test_logger_disabled(self):
        """测试禁用日志时不记录"""
        logger = BacktestLogger(enabled=False)
        bar = Bar(timestamp=1000, open=100, high=105, low=95, close=102, volume=1000)
        
        logger.log_bar(bar, equity=10000)
        logger.add_indicator("EMA", 100)
        logger.add_signal("Buy Signal")
        logger.commit()
        
        assert len(logger.get_entries()) == 0
    
    def test_log_bar_creates_entry(self):
        """测试 log_bar 创建条目"""
        logger = BacktestLogger(enabled=True)
        bar = Bar(timestamp=1000, open=100, high=105, low=95, close=102, volume=1000)
        
        logger.log_bar(bar, equity=10000, positions={"BTCUSDT": 1.5})
        logger.commit()
        
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].timestamp == 1000
        assert entries[0].equity == 10000
        assert entries[0].positions == {"BTCUSDT": 1.5}
        assert entries[0].bar_data["close"] == 102
    
    def test_add_indicator(self):
        """测试添加指标"""
        logger = BacktestLogger(enabled=True)
        bar = Bar(timestamp=1000, open=100, high=105, low=95, close=102, volume=1000)
        
        logger.log_bar(bar, equity=10000)
        logger.add_indicator("EMA20", 50000)
        logger.add_indicator("RSI", 45.5)
        logger.commit()
        
        entries = logger.get_entries()
        assert entries[0].indicators["EMA20"] == 50000
        assert entries[0].indicators["RSI"] == 45.5
    
    def test_add_signal(self):
        """测试添加信号"""
        logger = BacktestLogger(enabled=True)
        bar = Bar(timestamp=1000, open=100, high=105, low=95, close=102, volume=1000)
        
        logger.log_bar(bar, equity=10000)
        logger.add_signal("Golden Cross")
        logger.add_signal("RSI Oversold")
        logger.commit()
        
        entries = logger.get_entries()
        assert len(entries[0].signals) == 2
        assert "Golden Cross" in entries[0].signals
    
    def test_add_order(self):
        """测试添加订单"""
        logger = BacktestLogger(enabled=True)
        bar = Bar(timestamp=1000, open=100, high=105, low=95, close=102, volume=1000)
        order = Order(
            id="order-1",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            status=OrderStatus.FILLED
        )
        
        logger.log_bar(bar, equity=10000)
        logger.add_order(order)
        logger.commit()
        
        entries = logger.get_entries()
        assert len(entries[0].orders) == 1
        assert entries[0].orders[0]["symbol"] == "BTCUSDT"
        assert entries[0].orders[0]["side"] == "BUY"
    
    def test_add_note(self):
        """测试添加备注"""
        logger = BacktestLogger(enabled=True)
        bar = Bar(timestamp=1000, open=100, high=105, low=95, close=102, volume=1000)
        
        logger.log_bar(bar, equity=10000)
        logger.add_note("测试备注")
        logger.commit()
        
        entries = logger.get_entries()
        assert entries[0].notes == "测试备注"
    
    def test_multiple_entries(self):
        """测试多条日志"""
        logger = BacktestLogger(enabled=True)
        
        for i in range(5):
            bar = Bar(timestamp=1000 + i, open=100, high=105, low=95, close=102, volume=1000)
            logger.log_bar(bar, equity=10000 + i * 100)
            logger.commit()
        
        entries = logger.get_entries()
        assert len(entries) == 5
        assert entries[0].timestamp == 1000
        assert entries[4].timestamp == 1004
    
    def test_clear(self):
        """测试清空日志"""
        logger = BacktestLogger(enabled=True)
        bar = Bar(timestamp=1000, open=100, high=105, low=95, close=102, volume=1000)
        
        logger.log_bar(bar, equity=10000)
        logger.commit()
        assert len(logger.get_entries()) == 1
        
        logger.clear()
        assert len(logger.get_entries()) == 0
