# src/backtest/commission.py
"""
手续费模型

支持 Maker/Taker 费率区分和按交易对配置。
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CommissionScheme:
    """手续费配置
    
    Attributes:
        maker_fee: Maker 费率（挂单成交），默认 0.1%
        taker_fee: Taker 费率（吃单成交），默认 0.1%
        min_fee: 最低手续费
        
    Example:
        >>> scheme = CommissionScheme(taker_fee=0.001)
        >>> fee = scheme.calculate(size=1.0, price=50000.0)
        50.0  # 1 * 50000 * 0.001
    """
    maker_fee: float = 0.001  # 0.1%
    taker_fee: float = 0.001  # 0.1%
    min_fee: float = 0.0
    
    def calculate(
        self, 
        size: float, 
        price: float, 
        is_maker: bool = False
    ) -> float:
        """计算手续费
        
        Args:
            size: 成交数量
            price: 成交价格
            is_maker: 是否为 Maker 订单
            
        Returns:
            手续费金额
        """
        trade_value = abs(size) * price
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        fee = trade_value * fee_rate
        return max(fee, self.min_fee)


class CommissionManager:
    """手续费管理器
    
    支持按交易对配置不同的手续费方案。
    
    Example:
        >>> manager = CommissionManager()
        >>> manager.set_scheme(CommissionScheme(taker_fee=0.001))  # 默认
        >>> manager.set_scheme(CommissionScheme(taker_fee=0.0005), "BTCUSDT")  # BTC 特惠
        >>> fee = manager.calculate("BTCUSDT", 1.0, 50000.0)
        25.0  # 使用 BTC 专属费率
    """
    
    def __init__(self, default_scheme: CommissionScheme | None = None):
        """初始化手续费管理器
        
        Args:
            default_scheme: 默认手续费方案
        """
        self._default_scheme = default_scheme or CommissionScheme()
        self._schemes: Dict[str, CommissionScheme] = {}
    
    def set_scheme(
        self, 
        scheme: CommissionScheme, 
        symbol: str | None = None
    ) -> "CommissionManager":
        """设置手续费方案
        
        Args:
            scheme: 手续费配置
            symbol: 交易对，如果为 None 则设置为默认方案
            
        Returns:
            self，支持链式调用
        """
        if symbol is None:
            self._default_scheme = scheme
        else:
            self._schemes[symbol] = scheme
        return self
    
    def get_scheme(self, symbol: str) -> CommissionScheme:
        """获取指定交易对的手续费方案
        
        Args:
            symbol: 交易对
            
        Returns:
            手续费配置，如果没有专属配置则返回默认方案
        """
        return self._schemes.get(symbol, self._default_scheme)
    
    def calculate(
        self, 
        symbol: str, 
        size: float, 
        price: float, 
        is_maker: bool = False
    ) -> float:
        """计算手续费
        
        Args:
            symbol: 交易对
            size: 成交数量
            price: 成交价格
            is_maker: 是否为 Maker 订单
            
        Returns:
            手续费金额
        """
        scheme = self.get_scheme(symbol)
        return scheme.calculate(size, price, is_maker)
    
    def reset(self) -> None:
        """重置所有配置"""
        self._default_scheme = CommissionScheme()
        self._schemes.clear()
