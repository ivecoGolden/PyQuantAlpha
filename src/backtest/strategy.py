# src/backtest/strategy.py
"""
策略基类

为策略提供类型提示和 IDE 自动补全支持。
策略可以继承此基类，或作为"鸭子类型"独立存在（向后兼容）。

Example:
    # 使用基类（推荐）
    class MyStrategy(Strategy):
        def init(self):
            self.ema = EMA(20)
        
        def on_bar(self, bar):
            if self.ema.update(bar.close) > bar.close:
                self.order("BTCUSDT", "BUY", 1.0)
    
    # 鸭子类型（向后兼容）
    class Strategy:
        def init(self): ...
        def on_bar(self, bar): ...
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from src.backtest.models import Order, Position
    from src.data.models import Bar


class Strategy(ABC):
    """策略抽象基类
    
    定义策略必须实现的方法和可用的交易 API。
    
    Attributes:
        order: 下单函数（由 Engine 注入）
        close: 平仓函数（由 Engine 注入）
        get_position: 获取持仓函数（由 Engine 注入）
        get_cash: 获取可用资金函数（由 Engine 注入）
        get_equity: 获取账户净值函数（由 Engine 注入）
        get_bars: 获取历史 K 线函数（由 Engine 注入）
        get_bar: 获取指定位置 K 线函数（由 Engine 注入）
    """
    
    # ============ 交易 API（由 Engine 注入） ============
    
    def order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        exectype: str = None,
        trigger: Optional[float] = None
    ) -> "Order":
        """下单
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            side: "BUY" 或 "SELL"
            quantity: 数量
            price: 限价单价格（可选，默认市价单）
            exectype: 订单类型 "MARKET", "LIMIT", "STOP", "STOP_LIMIT"
            trigger: 止损触发价格（STOP/STOP_LIMIT 必填）
            
        Returns:
            Order 对象
        """
        raise NotImplementedError("order() 由 Engine 在运行时注入")
    
    def close(self, symbol: str) -> Optional["Order"]:
        """平仓
        
        Args:
            symbol: 交易对
            
        Returns:
            Order 对象，如果无持仓返回 None
        """
        raise NotImplementedError("close() 由 Engine 在运行时注入")
    
    def get_position(self, symbol: str) -> Optional["Position"]:
        """获取持仓
        
        Args:
            symbol: 交易对
            
        Returns:
            Position 对象，如果无持仓返回 None
        """
        raise NotImplementedError("get_position() 由 Engine 在运行时注入")
    
    def get_cash(self) -> float:
        """获取可用资金
        
        Returns:
            当前可用现金
        """
        raise NotImplementedError("get_cash() 由 Engine 在运行时注入")
    
    def get_equity(self) -> float:
        """获取账户净值
        
        Returns:
            账户净值（现金 + 持仓市值）
        """
        raise NotImplementedError("get_equity() 由 Engine 在运行时注入")
    
    def get_bars(self, symbol: str = None, lookback: int = 100) -> "Union[List[Bar], List[dict]]":
        """获取历史 K 线
        
        Args:
            symbol: 交易对 (可选)
            lookback: 获取的数量，默认 100
            
        Returns:
            如果指定 symbol，返回 List[Bar]
            如果未指定且为多资产模式，返回 List[Dict[str, Bar]]
            如果未指定且为单资产模式，返回 List[Bar]
        """
        raise NotImplementedError("get_bars() 由 Engine 在运行时注入")
    
    def get_bar(self, symbol: str = None, offset: int = -1) -> Optional["Bar"]:
        """获取指定位置的 K 线
        
        Args:
            symbol: 交易对 (可选)
            offset: 索引，-1 表示当前，-2 表示上一根
            
        Returns:
            Bar 对象
        """
        raise NotImplementedError("get_bar() 由 Engine 在运行时注入")
    
    # ============ 策略回调（可选实现） ============
    
    def notify_order(self, order: "Order") -> None:
        """订单状态变化回调
        
        当订单状态发生变化（提交、成交、拒绝等）时调用。
        
        Args:
            order: 订单对象
        """
        pass
    
    def notify_trade(self, trade) -> None:
        """成交回调
        
        当产生盈亏时调用（平仓成交）。
        
        Args:
            trade: Trade 对象
        """
        pass
    
    # ============ 必须实现的方法 ============
    
    @abstractmethod
    def init(self) -> None:
        """策略初始化
        
        在回测开始前调用，用于初始化指标、变量等。
        """
        pass
    
    @abstractmethod
    def on_bar(self, bar: "Union[Bar, Dict[str, Bar]]") -> None:
        """K 线回调
        
        每根 K 线到来时调用，是策略的主要逻辑入口。
        
        Args:
            bar: 当前 K 线数据
                 - 单资产模式: Bar 对象
                 - 多资产模式: Dict[str, Bar] 对象
        """
        pass
