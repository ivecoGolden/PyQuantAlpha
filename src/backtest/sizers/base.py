# src/backtest/sizers/base.py
"""
Sizer 基础架构

将 "交易什么" (Strategy) 与 "交易多少" (Sizer) 解耦：
- 策略只负责生成信号（买/卖）
- Sizer 根据账户状态、风险参数自动计算最优仓位
- 同一策略可配置不同 Sizer 适配不同资金规模
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backtest.broker import BacktestBroker


@dataclass
class SizerParams:
    """Sizer 通用参数
    
    Attributes:
        stake: 固定下单数量 (用于 FixedSize)
        percent: 资金占比 0-100 (用于 PercentSize)
        risk_percent: 单次风险比例 0-100 (用于 RiskSize)
        atr_period: ATR 计算周期 (用于 RiskSize)
        atr_multiplier: ATR 倍数，用于计算止损距离 (用于 RiskSize)
    """
    stake: float = 1.0
    percent: float = 20.0
    risk_percent: float = 2.0
    atr_period: int = 14
    atr_multiplier: float = 2.0


class BaseSizer(ABC):
    """Sizer 基类 - 所有 Sizer 必须继承此类
    
    Sizer 负责根据账户状态和风险参数计算下单数量。
    策略调用 buy()/sell() 时，如果未指定 size，则自动调用 Sizer 计算。
    
    Example:
        >>> sizer = PercentSize(SizerParams(percent=30))
        >>> sizer.set_broker(broker)
        >>> size = sizer.get_size(data, isbuy=True)
    """
    
    def __init__(self, params: SizerParams | None = None):
        """初始化 Sizer
        
        Args:
            params: Sizer 参数，如果为 None 则使用默认参数
        """
        self.params = params or SizerParams()
        self._broker: "BacktestBroker | None" = None
        self._strategy: Any = None
    
    def set_broker(self, broker: "BacktestBroker") -> "BaseSizer":
        """注入 Broker 依赖
        
        Args:
            broker: 回测经纪商实例
            
        Returns:
            self，支持链式调用
        """
        self._broker = broker
        return self
    
    def set_strategy(self, strategy: Any) -> "BaseSizer":
        """注入 Strategy 依赖
        
        Args:
            strategy: 策略实例，用于访问指标等数据
            
        Returns:
            self，支持链式调用
        """
        self._strategy = strategy
        return self
    
    @abstractmethod
    def get_size(self, data: Any, isbuy: bool) -> float:
        """计算下单数量（核心方法）
        
        Args:
            data: 目标数据源，可以是 Bar 对象或数据字典
            isbuy: True=买入, False=卖出
            
        Returns:
            float: 下单数量（正数）
                   返回 0 表示不交易
                   
        Note:
            - 返回值始终为正数，买卖方向由 isbuy 参数决定
            - 子类实现时需要检查 _broker 是否已注入
        """
        raise NotImplementedError
    
    @property
    def cash(self) -> float:
        """当前可用现金"""
        if self._broker is None:
            return 0.0
        return self._broker.cash
    
    @property
    def equity(self) -> float:
        """当前账户净值（现金 + 持仓市值）
        
        Note:
            需要提供当前价格才能精确计算，这里返回初始资金作为近似值
        """
        if self._broker is None:
            return 0.0
        # 简化处理：使用 cash 作为近似值
        # 精确值需要通过 broker.get_value(prices) 获取
        return self._broker.cash
    
    def get_position(self, symbol: str | None = None):
        """获取当前持仓
        
        Args:
            symbol: 交易对，如果为 None 则返回默认交易对的持仓
            
        Returns:
            Position 对象，如果无持仓返回 None
        """
        if self._broker is None:
            return None
        # 如果未指定 symbol，尝试从 positions 中获取第一个
        if symbol is None:
            positions = self._broker.positions
            if positions:
                return next(iter(positions.values()))
            return None
        return self._broker.get_position(symbol)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(params={self.params})"
