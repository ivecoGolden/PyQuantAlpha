# src/data/resampler.py
"""数据重采样模块

将低频 K 线（如 1m）动态合成高频 K 线（如 5m, 1h, 4h）。
支持 OHLCV 核心字段及 Phase 3 扩展字段。
"""

from __future__ import annotations
from typing import List, Optional, Dict
from .models import Bar
from .binance import INTERVAL_MS

class Resampler:
    """K 线重采样器
    
    用于将基础 K 线数据（通常是 1m）聚合为更高周期的数据。
    
    Example:
        >>> bars_1m = [...]
        >>> bars_1h = Resampler.resample(bars_1m, "1h")
    """
    
    @staticmethod
    def resample(bars: List[Bar], target_interval: str) -> List[Bar]:
        """对 K 线数据进行重采样
        
        Args:
            bars: 原始 K 线数据（建议为 1m）
            target_interval: 目标周期，如 "5m", "1h", "4h", "1d"
            
        Returns:
            重采样后的 K 线列表
            
        Raises:
            ValueError: 目标周期无效
        """
        if not bars:
            return []
            
        if target_interval not in INTERVAL_MS:
            raise ValueError(f"无效的目标周期: {target_interval}")
            
        target_ms = INTERVAL_MS[target_interval]
        
        # 结果列表
        resampled_bars: List[Bar] = []
        
        # 当前聚合桶的状态
        current_bucket_start: Optional[int] = None
        current_open: float = 0.0
        current_high: float = -float('inf')
        current_low: float = float('inf')
        current_close: float = 0.0
        current_volume: float = 0.0
        current_quote_volume: float = 0.0
        current_trade_count: int = 0
        current_taker_buy_base: float = 0.0
        current_taker_buy_quote: float = 0.0
        
        for bar in bars:
            # 计算该 bar 所属的桶开始时间
            bucket_start = (bar.timestamp // target_ms) * target_ms
            
            if current_bucket_start is None:
                # 初始化第一个桶
                current_bucket_start = bucket_start
                current_open = bar.open
                current_high = bar.high
                current_low = bar.low
                current_close = bar.close
                current_volume = bar.volume
                current_quote_volume = bar.quote_volume
                current_trade_count = bar.trade_count
                current_taker_buy_base = bar.taker_buy_base
                current_taker_buy_quote = bar.taker_buy_quote
            elif bucket_start == current_bucket_start:
                # 继续在当前桶内聚合
                current_high = max(current_high, bar.high)
                current_low = min(current_low, bar.low)
                current_close = bar.close
                current_volume += bar.volume
                current_quote_volume += bar.quote_volume
                current_trade_count += bar.trade_count
                current_taker_buy_base += bar.taker_buy_base
                current_taker_buy_quote += bar.taker_buy_quote
            else:
                # 桶切换：先保存旧桶，再初始化新桶
                resampled_bars.append(Bar(
                    timestamp=current_bucket_start,
                    open=current_open,
                    high=current_high,
                    low=current_low,
                    close=current_close,
                    volume=current_volume,
                    close_time=current_bucket_start + target_ms - 1,
                    quote_volume=current_quote_volume,
                    trade_count=current_trade_count,
                    taker_buy_base=current_taker_buy_base,
                    taker_buy_quote=current_taker_buy_quote
                ))
                
                # 初始化新桶
                current_bucket_start = bucket_start
                current_open = bar.open
                current_high = bar.high
                current_low = bar.low
                current_close = bar.close
                current_volume = bar.volume
                current_quote_volume = bar.quote_volume
                current_trade_count = bar.trade_count
                current_taker_buy_base = bar.taker_buy_base
                current_taker_buy_quote = bar.taker_buy_quote
        
        # 循环结束，处理最后一个桶
        if current_bucket_start is not None:
             resampled_bars.append(Bar(
                timestamp=current_bucket_start,
                open=current_open,
                high=current_high,
                low=current_low,
                close=current_close,
                volume=current_volume,
                close_time=current_bucket_start + target_ms - 1,
                quote_volume=current_quote_volume,
                trade_count=current_trade_count,
                taker_buy_base=current_taker_buy_base,
                taker_buy_quote=current_taker_buy_quote
            ))
            
        return resampled_bars
