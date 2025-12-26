# src/backtest/analyzers/base.py
"""
分析器基类

所有分析器必须继承 BaseAnalyzer 并实现 calculate() 方法。
分析器在回测结束后被调用，用于计算各种绩效指标。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class AnalyzerResult:
    """分析器结果
    
    Attributes:
        name: 分析器名称
        value: 主要指标值
        details: 详细信息字典
    """
    name: str
    value: float
    details: Optional[Dict[str, Any]] = None


class BaseAnalyzer(ABC):
    """分析器基类
    
    所有分析器必须继承此类并实现 calculate() 方法。
    
    Example:
        >>> class MyAnalyzer(BaseAnalyzer):
        ...     def calculate(self, equity_curve, trades) -> AnalyzerResult:
        ...         # 计算逻辑
        ...         return AnalyzerResult(name="My Metric", value=0.5)
    """
    
    def __init__(self, name: str = "BaseAnalyzer") -> None:
        self.name = name
    
    @abstractmethod
    def calculate(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Any],
        initial_capital: float = 100000.0
    ) -> AnalyzerResult:
        """计算分析指标
        
        Args:
            equity_curve: 净值曲线 [{"timestamp": int, "equity": float}, ...]
            trades: 交易列表
            initial_capital: 初始资金
            
        Returns:
            AnalyzerResult: 分析结果
        """
        raise NotImplementedError
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
