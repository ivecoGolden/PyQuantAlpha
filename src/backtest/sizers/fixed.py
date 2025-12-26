# src/backtest/sizers/fixed.py
"""
固定数量 Sizer

始终返回固定的下单数量，适用于简单策略或测试场景。
"""

from typing import Any

from src.backtest.sizers.base import BaseSizer, SizerParams


class FixedSize(BaseSizer):
    """固定数量 Sizer
    
    无论账户状态如何，始终返回固定的下单数量。
    
    Example:
        >>> sizer = FixedSize(SizerParams(stake=0.1))
        >>> sizer.get_size(data, isbuy=True)
        0.1
    """
    
    def get_size(self, data: Any, isbuy: bool) -> float:
        """返回固定下单数量
        
        Args:
            data: 数据源（本 Sizer 不使用）
            isbuy: 买卖方向（本 Sizer 不使用）
            
        Returns:
            params.stake 指定的固定数量
        """
        return self.params.stake
