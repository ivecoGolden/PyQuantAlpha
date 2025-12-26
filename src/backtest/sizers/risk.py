# src/backtest/sizers/risk.py
"""
基于风险的 Sizer

根据 ATR（平均真实波幅）和风险比例计算下单数量。
核心思想：控制单笔交易的最大亏损不超过账户的指定百分比。
"""

from typing import Any

from src.backtest.sizers.base import BaseSizer, SizerParams


class RiskSize(BaseSizer):
    """基于 ATR 的风险仓位管理
    
    计算公式：
        风险金额 = 账户净值 × 风险比例
        止损距离 = ATR × ATR倍数
        仓位 = 风险金额 / 止损距离
    
    Example:
        >>> # 账户净值 $10,000，风险 2%，ATR = 50，ATR倍数 = 2
        >>> # 风险金额 = 10000 * 0.02 = 200
        >>> # 止损距离 = 50 * 2 = 100
        >>> # 仓位 = 200 / 100 = 2
        >>> sizer = RiskSize(SizerParams(risk_percent=2, atr_multiplier=2))
        >>> sizer.set_broker(broker).set_strategy(strategy)
        >>> sizer.get_size(data, isbuy=True)
        2.0
        
    Note:
        需要在策略中预计算 ATR 指标，并通过 self.atr 属性暴露。
        如果无法获取 ATR，将回退到固定数量 (params.stake)。
    """
    
    def get_size(self, data: Any, isbuy: bool) -> float:
        """基于 ATR 风险计算下单数量
        
        Args:
            data: 数据源
            isbuy: 买卖方向
            
        Returns:
            计算后的下单数量，无法计算时返回 params.stake
        """
        if self._broker is None:
            return 0.0
        
        # 获取 ATR 值
        atr_value = self._get_atr_value()
        if atr_value is None or atr_value <= 0:
            # 回退到固定数量
            return self.params.stake
        
        # 计算账户净值（使用可用现金作为近似）
        equity = self.cash
        if equity <= 0:
            return 0.0
        
        # 风险金额 = 账户净值 × 风险比例
        risk_amount = equity * (self.params.risk_percent / 100.0)
        
        # 止损距离 = ATR × 倍数
        stop_distance = atr_value * self.params.atr_multiplier
        
        if stop_distance <= 0:
            return self.params.stake
        
        # 仓位 = 风险金额 / 止损距离
        size = risk_amount / stop_distance
        
        return size
    
    def _get_atr_value(self) -> float | None:
        """从策略中获取 ATR 值
        
        尝试多种方式获取 ATR：
        1. strategy.atr 属性
        2. strategy.atr[0] (类数组)
        3. strategy.atr.value 或 strategy.atr.current
        
        Returns:
            ATR 值，无法获取时返回 None
        """
        if self._strategy is None:
            return None
        
        atr = getattr(self._strategy, 'atr', None)
        if atr is None:
            return None
        
        # 情况1：atr 直接是数值
        if isinstance(atr, (int, float)):
            return float(atr)
        
        # 情况2：atr 是类数组（如 deque 或 list）
        if hasattr(atr, '__getitem__'):
            try:
                return float(atr[0])
            except (IndexError, TypeError, KeyError):
                pass
        
        # 情况3：atr 是指标对象，有 value 或 current 属性
        if hasattr(atr, 'value'):
            val = atr.value
            if val is not None:
                return float(val)
        
        if hasattr(atr, 'current'):
            val = atr.current
            if val is not None:
                return float(val)
        
        # 情况4：atr 是指标对象，调用后返回值
        if callable(atr):
            try:
                val = atr()
                if val is not None:
                    return float(val)
            except Exception:
                pass
        
        return None
