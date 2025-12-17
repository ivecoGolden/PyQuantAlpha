# tests/test_backtest/test_hooks.py
"""Phase 2.1: 策略钩子和可视化日志测试"""

import pytest
from src.backtest.engine import BacktestEngine
from src.backtest.logger import BacktestLogger
from src.backtest.models import Order, OrderSide, OrderStatus, Trade
from src.data.models import Bar


# ============ 测试数据 ============

def make_bar(timestamp: int, close: float) -> Bar:
    """创建测试用 Bar"""
    return Bar(
        timestamp=timestamp,
        open=close,
        high=close * 1.01,
        low=close * 0.99,
        close=close,
        volume=1000.0
    )


SIMPLE_STRATEGY = """
class Strategy:
    def init(self):
        self.bought = False
        self.order_notifications = []
        self.trade_notifications = []
    
    def notify_order(self, order):
        self.order_notifications.append(order)
    
    def notify_trade(self, trade):
        self.trade_notifications.append(trade)
    
    def on_bar(self, bar):
        if not self.bought:
            self.order("BTCUSDT", "BUY", 1.0)
            self.bought = True
        elif len(self.order_notifications) > 0:
            # 第二根 K 线卖出
            self.order("BTCUSDT", "SELL", 1.0)
"""


# ============ Strategy Hooks 测试 ============

class TestNotifyOrder:
    """测试 notify_order 回调"""
    
    def test_notify_order_called_on_fill(self):
        """订单成交时应触发 notify_order"""
        engine = BacktestEngine()
        bars = [make_bar(1000, 100.0), make_bar(2000, 105.0)]
        
        result = engine.run(SIMPLE_STRATEGY, bars)
        
        # 策略内部记录了通知
        assert len(engine._strategy.order_notifications) >= 1
        assert engine._strategy.order_notifications[0].status == OrderStatus.FILLED
    
    def test_notify_order_receives_correct_order(self):
        """notify_order 应收到正确的 Order 对象"""
        engine = BacktestEngine()
        bars = [make_bar(1000, 100.0), make_bar(2000, 105.0)]
        
        engine.run(SIMPLE_STRATEGY, bars)
        
        order = engine._strategy.order_notifications[0]
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.quantity == 1.0


class TestNotifyTrade:
    """测试 notify_trade 回调"""
    
    def test_notify_trade_called_on_close(self):
        """平仓时应触发 notify_trade"""
        engine = BacktestEngine()
        # 需要至少 3 根 K 线：买入、卖出成交、确认
        bars = [
            make_bar(1000, 100.0),
            make_bar(2000, 105.0),
            make_bar(3000, 110.0)
        ]
        
        engine.run(SIMPLE_STRATEGY, bars)
        
        # 应该有平仓通知（卖出产生盈亏）
        assert len(engine._strategy.trade_notifications) >= 1
    
    def test_notify_trade_has_pnl(self):
        """notify_trade 的 Trade 对象应包含盈亏"""
        engine = BacktestEngine()
        bars = [
            make_bar(1000, 100.0),
            make_bar(2000, 105.0),
            make_bar(3000, 110.0)
        ]
        
        engine.run(SIMPLE_STRATEGY, bars)
        
        if engine._strategy.trade_notifications:
            trade = engine._strategy.trade_notifications[0]
            # 卖出时应有盈亏
            assert trade.pnl != 0


# ============ Logger 可视化数据测试 ============

class TestLoggerVisualization:
    """测试 BacktestLogger 的可视化数据收集"""
    

    def test_log_order_event_populates_order_logs(self):
        """log_order_event 应填充 order_logs 列表"""
        logger = BacktestLogger(enabled=True)
        
        order = Order(
            id="O001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=None,
            quantity=0.5,
            created_at=1000000,
            status=OrderStatus.FILLED,
            filled_avg_price=51000.0
        )
        
        logger.log_order_event(order)
        
        assert len(logger.order_logs) == 1
        assert "SELL" in logger.order_logs[0]["msg"]
        assert logger.order_logs[0]["level"] == "ORDER"
    
    def test_log_trade_event_populates_trade_logs(self):
        """log_trade_event 应填充 trade_logs 列表"""
        logger = BacktestLogger(enabled=True)
        
        trade = Trade(
            id="T001",
            order_id="O001",
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            price=3000.0,
            quantity=2.0,
            fee=6.0,
            timestamp=2000000,
            pnl=150.0
        )
        
        logger.log_trade_event(trade)
        
        assert len(logger.trade_logs) == 1
        assert logger.trade_logs[0]["pnl"] == 150.0
        assert logger.trade_logs[0]["symbol"] == "ETHUSDT"
    
    def test_clear_resets_visualization_data(self):
        """clear 应重置可视化数据"""
        logger = BacktestLogger(enabled=True)
        
        # 添加一些数据
        # 添加一些数据
        logger.order_logs.append({"msg": "test"})
        logger.trade_logs.append({"pnl": 100})
        
        logger.clear()
        
        assert len(logger.order_logs) == 0
        assert len(logger.trade_logs) == 0


# ============ Engine 集成测试 ============

class TestEngineVisualsIntegration:
    """测试 Engine 与 Logger 可视化的集成"""
    

    def test_engine_populates_order_logs(self):
        """回测后 logger 应包含 order_logs"""
        engine = BacktestEngine()
        bars = [
            make_bar(1000, 100.0),
            make_bar(2000, 105.0)
        ]
        
        engine.run(SIMPLE_STRATEGY, bars)
        
        assert len(engine._logger.order_logs) >= 1
