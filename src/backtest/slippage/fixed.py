# src/backtest/slippage/fixed.py
"""
固定滑点模型

无论订单大小和价格，始终应用固定金额的滑点。
"""

from src.backtest.slippage.base import BaseSlippage, SlippageParams


class FixedSlippage(BaseSlippage):
    """固定金额滑点
    
    成交价格 = 原价格 ± 固定金额
    
    Example:
        >>> slippage = FixedSlippage(SlippageParams(fixed_amount=0.01))
        >>> slippage.calculate(100.0, 1.0, is_buy=True)
        100.01  # 买入时价格上涨
        >>> slippage.calculate(100.0, 1.0, is_buy=False)
        99.99   # 卖出时价格下跌
    """
    
    def calculate(self, price: float, size: float, is_buy: bool) -> float:
        """计算固定滑点后的价格
        
        Args:
            price: 原始价格
            size: 下单数量（本模型不使用）
            is_buy: 买卖方向
            
        Returns:
            滑点后的价格
        """
        slip = self.params.fixed_amount
        return price + slip if is_buy else price - slip
