# src/backtest/slippage/base.py
"""
滑点模型基础架构

滑点模型用于模拟真实交易中的价格滑移，提升回测的仿真精度。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SlippageParams:
    """滑点模型参数
    
    Attributes:
        fixed_amount: 固定金额滑点
        percent: 百分比滑点 (0.001 = 0.1%)
        volume_impact: 成交量影响系数（用于 VolumeSlippage）
    """
    fixed_amount: float = 0.0
    percent: float = 0.0
    volume_impact: float = 0.1


class BaseSlippage(ABC):
    """滑点模型基类
    
    所有滑点模型必须继承此类并实现 calculate 方法。
    
    滑点规则：
    - 买入时滑点增加成交价格（对买方不利）
    - 卖出时滑点减少成交价格（对卖方不利）
    """
    
    def __init__(self, params: SlippageParams | None = None):
        """初始化滑点模型
        
        Args:
            params: 滑点参数，如果为 None 则使用默认参数
        """
        self.params = params or SlippageParams()
    
    @abstractmethod
    def calculate(self, price: float, size: float, is_buy: bool) -> float:
        """计算滑点后的成交价格
        
        Args:
            price: 原始价格
            size: 下单数量
            is_buy: True=买入, False=卖出
            
        Returns:
            滑点后的成交价格
        """
        raise NotImplementedError
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(params={self.params})"
