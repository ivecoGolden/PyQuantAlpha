# src/backtest/logger.py
"""
回测日志系统

提供两类日志功能：

1. **分步日志** (entries)
   - 每根 K 线的指标、信号、订单、持仓
   - 用于策略调试和复盘

2. **可视化日志** (Phase 2.1)
   - order_logs: 订单流水 [{time, level, msg}]
   - trade_logs: 交易明细 [{time, symbol, pnl, ...}]
   - markers: 图表标记点 [{x, y, type, text}]
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
        
        # Phase 2.1: 可视化数据收集
        self.order_logs: List[dict] = []   # 订单流水
        self.trade_logs: List[dict] = []   # 交易流水（含盈亏）
        self.markers: List[dict] = []       # 买卖标记点
    
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
        # Phase 2.1: 清空可视化数据
        self.order_logs.clear()
        self.trade_logs.clear()
        self.markers.clear()
    
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
    
    # ============ Phase 2.1: 可视化日志方法 ============
    
    def log_order_event(self, order, equity: float) -> None:
        """记录订单事件（用于前端可视化）
        
        Args:
            order: Order 对象
            equity: 当前净值（用于 marker Y 坐标）
        """
        if not self.enabled:
            return
        
        from datetime import datetime
        time_str = datetime.fromtimestamp(order.created_at / 1000).strftime("%Y-%m-%d %H:%M:%S")
        
        self.order_logs.append({
            "time": time_str,
            "level": "ORDER",
            "msg": f"{order.status.value}: {order.side.value} {order.symbol} {order.quantity:.4f} @ {order.filled_avg_price:.2f}"
        })
        
        # 添加图表标记
        self.markers.append({
            "x": order.created_at,
            "y": equity,
            "type": order.side.value,
            "text": f"{order.side.value} {order.quantity:.4f} @ {order.filled_avg_price:.2f}"
        })
    
    def log_trade_event(self, trade) -> None:
        """记录交易事件（平仓盈亏，用于前端可视化）
        
        Args:
            trade: Trade 对象
        """
        if not self.enabled:
            return
        
        from datetime import datetime
        time_str = datetime.fromtimestamp(trade.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
        
        pnl_str = f"+{trade.pnl:.2f}" if trade.pnl >= 0 else f"{trade.pnl:.2f}"
        
        self.trade_logs.append({
            "time": time_str,
            "symbol": trade.symbol,
            "side": trade.side.value,
            "price": trade.price,
            "quantity": trade.quantity,
            "pnl": trade.pnl,
            "fee": trade.fee
        })
        
        self.order_logs.append({
            "time": time_str,
            "level": "TRADE",
            "msg": f"平仓: {trade.symbol} PnL: {pnl_str}"
        })

