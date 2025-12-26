# src/backtest/slippage/percent.py
"""
百分比滑点模型

根据价格的百分比计算滑点，更贴近真实市场行为。
"""

from src.backtest.slippage.base import BaseSlippage, SlippageParams


class PercentSlippage(BaseSlippage):
    """百分比滑点
    
    成交价格 = 原价格 × (1 ± 滑点比例)
    
    Example:
        >>> # 0.1% 滑点
        >>> slippage = PercentSlippage(SlippageParams(percent=0.001))
        >>> slippage.calculate(100.0, 1.0, is_buy=True)
        100.1   # 100 * (1 + 0.001)
        >>> slippage.calculate(100.0, 1.0, is_buy=False)
        99.9    # 100 * (1 - 0.001)
    """
    
    def calculate(self, price: float, size: float, is_buy: bool) -> float:
        """计算百分比滑点后的价格
        
        Args:
            price: 原始价格
            size: 下单数量（本模型不使用）
            is_buy: 买卖方向
            
        Returns:
            滑点后的价格
        """
        slip = price * self.params.percent
        return price + slip if is_buy else price - slip


class VolumeSlippage(BaseSlippage):
    """成交量滑点模型
    
    根据订单量占市场成交量的比例动态计算滑点。
    订单越大，滑点越大（模拟冲击成本）。
    
    计算公式:
        滑点比例 = (订单量 / 市场成交量) × 影响系数
        成交价格 = 原价格 × (1 ± 滑点比例)
    
    Note:
        需要提供 market_volume 参数才能使用此模型。
        如果未提供，将回退到 0 滑点。
    """
    
    def calculate(
        self, 
        price: float, 
        size: float, 
        is_buy: bool,
        market_volume: float | None = None
    ) -> float:
        """计算成交量滑点后的价格
        
        Args:
            price: 原始价格
            size: 下单数量
            is_buy: 买卖方向
            market_volume: 市场成交量（可选）
            
        Returns:
            滑点后的价格
        """
        if market_volume is None or market_volume <= 0:
            return price
        
        # 计算冲击比例
        impact_ratio = abs(size) / market_volume
        slip = price * impact_ratio * self.params.volume_impact
        
        return price + slip if is_buy else price - slip
