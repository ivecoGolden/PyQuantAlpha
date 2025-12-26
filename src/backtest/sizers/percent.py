# src/backtest/sizers/percent.py
"""
百分比 Sizer

根据可用资金的百分比计算下单数量。
"""

from typing import Any

from src.backtest.sizers.base import BaseSizer, SizerParams


class PercentSize(BaseSizer):
    """按可用资金百分比计算仓位
    
    根据当前可用现金和指定百分比计算下单数量。
    
    Example:
        >>> # 账户有 $10,000，价格 $100，使用 50% 资金
        >>> sizer = PercentSize(SizerParams(percent=50))
        >>> sizer.set_broker(broker)  # broker.cash = 10000
        >>> sizer.get_size(bar, isbuy=True)  # bar.close = 100
        50.0  # 10000 * 0.5 / 100 = 50
    """
    
    def get_size(self, data: Any, isbuy: bool) -> float:
        """根据可用资金百分比计算下单数量
        
        Args:
            data: 数据源，需要有 close 属性或 'close' 键
            isbuy: True=买入, False=卖出
            
        Returns:
            计算后的下单数量，如果无法计算返回 0
        """
        if self._broker is None:
            return 0.0
        
        # 获取当前价格
        price = self._get_price(data)
        if price <= 0:
            return 0.0
        
        # 计算可用于交易的资金
        available_cash = self.cash * (self.params.percent / 100.0)
        
        # 计算下单数量
        size = available_cash / price
        
        return size
    
    def _get_price(self, data: Any) -> float:
        """从数据中提取价格
        
        Args:
            data: 数据源
            
        Returns:
            当前价格，无法获取时返回 0
        """
        # 尝试作为对象属性访问
        if hasattr(data, 'close'):
            close = data.close
            # 支持类数组访问（如 data.close[0]）
            if hasattr(close, '__getitem__'):
                try:
                    return float(close[0])
                except (IndexError, TypeError):
                    pass
            return float(close)
        
        # 尝试作为字典访问
        if isinstance(data, dict):
            if 'close' in data:
                return float(data['close'])
            # 可能是多资产模式 {symbol: bar}
            for val in data.values():
                if hasattr(val, 'close'):
                    return float(val.close)
        
        return 0.0


class AllIn(BaseSizer):
    """全仓 Sizer
    
    使用全部可用资金计算下单数量。
    等价于 PercentSize(SizerParams(percent=100))。
    
    Example:
        >>> sizer = AllIn()
        >>> sizer.set_broker(broker)
        >>> sizer.get_size(bar, isbuy=True)
    """
    
    def __init__(self, params: SizerParams | None = None):
        """初始化全仓 Sizer
        
        Args:
            params: 参数（percent 会被强制设为 100）
        """
        super().__init__(params)
        self.params.percent = 100.0
    
    def get_size(self, data: Any, isbuy: bool) -> float:
        """使用全部资金计算下单数量
        
        Args:
            data: 数据源
            isbuy: 买卖方向
            
        Returns:
            计算后的下单数量
        """
        if self._broker is None:
            return 0.0
        
        # 获取当前价格
        price = self._get_price(data)
        if price <= 0:
            return 0.0
        
        # 使用全部可用现金
        size = self.cash / price
        
        return size
    
    def _get_price(self, data: Any) -> float:
        """从数据中提取价格"""
        if hasattr(data, 'close'):
            close = data.close
            if hasattr(close, '__getitem__'):
                try:
                    return float(close[0])
                except (IndexError, TypeError):
                    pass
            return float(close)
        
        if isinstance(data, dict):
            if 'close' in data:
                return float(data['close'])
            for val in data.values():
                if hasattr(val, 'close'):
                    return float(val.close)
        
        return 0.0
