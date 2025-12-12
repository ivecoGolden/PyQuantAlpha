# src/backtest/logger.py
"""回测日志系统

提供详细的回测日志记录功能，便于策略调试和复盘。
"""

import json
import logging
from typing import List, Optional
from dataclasses import asdict

from src.data.models import Bar
from .models import BacktestLogEntry, Order, Position


logger = logging.getLogger(__name__)


class BacktestLogger:
    """回测日志记录器
    
    记录每一步的数据、指标、信号、订单和持仓信息。
    
    Example:
        >>> logger = BacktestLogger()
        >>> logger.log_bar(bar, equity=100000)
        >>> logger.add_indicator("EMA20", 50000)
        >>> logger.add_signal("Golden Cross")
        >>> logger.commit()  # 提交当前条目
    """
    
    def __init__(self, enabled: bool = True) -> None:
        """初始化日志记录器
        
        Args:
            enabled: 是否启用日志记录
        """
        self.enabled = enabled
        self.entries: List[BacktestLogEntry] = []
        self._current_entry: Optional[BacktestLogEntry] = None
    
    def log_bar(
        self, 
        bar: Bar, 
        equity: float = 0.0,
        position_qty: float = 0.0
    ) -> None:
        """开始记录新的一根 K 线
        
        Args:
            bar: K 线数据
            equity: 当前净值
            position_qty: 当前持仓数量
        """
        if not self.enabled:
            return
        
        self._current_entry = BacktestLogEntry(
            timestamp=bar.timestamp,
            bar_data={
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume
            },
            equity=equity,
            position_qty=position_qty
        )
    
    def add_indicator(self, name: str, value: float) -> None:
        """添加指标值
        
        Args:
            name: 指标名称
            value: 指标值
        """
        if not self.enabled or not self._current_entry:
            return
        self._current_entry.indicators[name] = value
    
    def add_signal(self, signal: str) -> None:
        """添加交易信号
        
        Args:
            signal: 信号描述
        """
        if not self.enabled or not self._current_entry:
            return
        self._current_entry.signals.append(signal)
    
    def add_order(self, order: Order) -> None:
        """添加订单记录
        
        Args:
            order: 订单对象
        """
        if not self.enabled or not self._current_entry:
            return
        self._current_entry.orders.append({
            "id": order.id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "status": order.status.value
        })
    
    def add_note(self, note: str) -> None:
        """添加备注
        
        Args:
            note: 备注文本
        """
        if not self.enabled or not self._current_entry:
            return
        self._current_entry.notes = note
    
    def commit(self) -> None:
        """提交当前日志条目"""
        if not self.enabled or not self._current_entry:
            return
        self.entries.append(self._current_entry)
        self._current_entry = None
    
    def get_entries(self) -> List[BacktestLogEntry]:
        """获取所有日志条目"""
        return self.entries
    
    def clear(self) -> None:
        """清空日志"""
        self.entries.clear()
        self._current_entry = None
    
    def export_jsonl(self, filepath: str) -> None:
        """导出为 JSON Lines 格式
        
        Args:
            filepath: 输出文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                line = json.dumps(asdict(entry), ensure_ascii=False)
                f.write(line + '\n')
        logger.info(f"日志已导出: {filepath} ({len(self.entries)} 条)")
