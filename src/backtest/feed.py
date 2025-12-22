# src/backtest/feed.py
"""
数据源抽象

提供统一的数据迭代接口，支持单资产和多资产回测。

核心类:
- DataFeed: 抽象基类
- SingleFeed: 单资产数据源
- MultiFeed: 多资产数据源（时间对齐）

使用方式:
    feed = SingleFeed(bars)
    for bar in feed:
        engine.process(bar)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, Union

from src.data.models import Bar
from src.data.binance import INTERVAL_MS


class DataFeed(ABC):
    """数据源抽象基类
    
    定义回测数据遍历的统一接口。
    
    Attributes:
        symbols: 数据源包含的交易对列表
    """
    
    @property
    @abstractmethod
    def symbols(self) -> List[str]:
        """获取所有交易对"""
        pass
    
    @abstractmethod
    def __iter__(self) -> Iterator:
        """迭代数据"""
        pass
    
    @abstractmethod
    def __len__(self) -> int:
        """数据长度"""
        pass


class SingleFeed(DataFeed):
    """单资产数据源
    
    封装单个交易对的 K 线数据。
    
    Args:
        bars: K 线数据列表
        symbol: 交易对名称（默认从 Bar 中读取或使用 "DEFAULT"）
        
    Example:
        >>> bars = [Bar(...), Bar(...)]
        >>> feed = SingleFeed(bars, symbol="BTCUSDT")
        >>> for bar in feed:
        ...     print(bar.close)
    """
    
    def __init__(self, bars: List[Bar], symbol: str = None):
        self._bars = bars
        self._symbol = symbol or (bars[0].symbol if bars and hasattr(bars[0], 'symbol') else "DEFAULT")
    
    @property
    def symbols(self) -> List[str]:
        return [self._symbol]
    
    @property
    def bars(self) -> List[Bar]:
        """原始 K 线数据"""
        return self._bars
    
    def __iter__(self) -> Iterator[Bar]:
        return iter(self._bars)
    
    def __len__(self) -> int:
        return len(self._bars)


class MultiFeed(DataFeed):
    """多资产数据源
    
    支持多个交易对的时间对齐迭代。
    
    Args:
        feeds: 多个 SingleFeed 的字典 {symbol: SingleFeed}
        
    Example:
        >>> btc_feed = SingleFeed(btc_bars, "BTCUSDT")
        >>> eth_feed = SingleFeed(eth_bars, "ETHUSDT")
        >>> feed = MultiFeed({"BTCUSDT": btc_feed, "ETHUSDT": eth_feed})
        >>> for bars_slice in feed:
        ...     # bars_slice = {"BTCUSDT": Bar, "ETHUSDT": Bar}
        ...     print(bars_slice["BTCUSDT"].close)
    """
    
    def __init__(self, feeds: Dict[str, SingleFeed]):
        self._feeds = feeds
        self._aligned_data: List[Dict[str, Bar]] = []
        self._align_data()
    
    def _align_data(self) -> None:
        """按时间戳对齐多个数据流
        
        策略: 并集时间轴 + 前值填充 (Forward Fill)
        """
        if not self._feeds:
            return
        
        # 收集所有时间戳（并集）
        timestamp_sets = []
        for feed in self._feeds.values():
            timestamps = {bar.timestamp for bar in feed.bars}
            timestamp_sets.append(timestamps)
        
        # 求并集（只要有任何数据源有数据的时间点）
        union_timestamps = set.union(*timestamp_sets) if timestamp_sets else set()
        sorted_timestamps = sorted(union_timestamps)
        
        # 构建时间戳到 Bar 的映射
        bar_maps: Dict[str, Dict[int, Bar]] = {}
        for symbol, feed in self._feeds.items():
            bar_maps[symbol] = {bar.timestamp: bar for bar in feed.bars}
        
        # 上一根有效的 Bar 缓存
        last_valid_bars: Dict[str, Bar] = {}
        
        # 按时间顺序生成对齐后的数据切片
        for ts in sorted_timestamps:
            slice_data = {}
            for symbol in self._feeds:
                # 尝试获取当前时间点的 Bar
                bar = bar_maps[symbol].get(ts)
                
                if bar:
                    # 有数据，更新缓存
                    last_valid_bars[symbol] = bar
                    slice_data[symbol] = bar
                elif symbol in last_valid_bars:
                    # 无数据，使用前值填充
                    slice_data[symbol] = last_valid_bars[symbol]
                else:
                    # 无数据且无前值（开始阶段缺失），该 symbol 在此时间点无数据
                    pass
            
            # 只有当切片不为空时才添加（理论上只要 ts 在 union_timestamps 中，至少有一个 symbol 有数据）
            if slice_data:
                self._aligned_data.append(slice_data)
    
    @property
    def symbols(self) -> List[str]:
        return list(self._feeds.keys())
    
    def __iter__(self) -> Iterator[Dict[str, Bar]]:
        return iter(self._aligned_data)
    
    def __len__(self) -> int:
        return len(self._aligned_data)


class TimeframeAlignedFeed(DataFeed):
    """多周期对齐数据源
    
    确保高频率数据在低频率步进时不会产生"未来函数"。
    例如：在 1m 回测中，1h 的 Bar 只有在整点结束后的下一分钟才对策略可见。
    
    Args:
        base_feed: 基础频率对（通常是 1m），Dict[str, List[Bar]]
        other_feeds: 其他频率对，Dict[str, Dict[str, List[Bar]]] 
                     格式: {interval: {symbol: List[Bar]}}
    """
    
    def __init__(self, base_feed: Dict[str, List[Bar]], other_feeds: Dict[str, Dict[str, List[Bar]]]):
        self._base_data = base_feed
        self._other_data = other_feeds
        self._symbols = list(base_feed.keys())
        self._aligned_data: List[Dict[str, Union[Bar, Dict[str, Bar]]]] = []
        self._align_timeframes()

    def _align_timeframes(self) -> None:
        """执行多周期对齐
        
        对齐逻辑：
        1. 以 base_feed 的时间戳作为主时间轴
        2. 对于每个主时间轴点 T：
           - 包含当前 T 的 base Bar
           - 对于其他周期 interval，查找最高时间戳但其 close_time < T 的 Bar
        """
        # 获取基础频率数据（通常所有交易对时间对齐，如果不对齐则取并集）
        ts_sets = []
        for bars in self._base_data.values():
            ts_sets.append({b.timestamp for b in bars})
        
        main_timeline = sorted(set.union(*ts_sets))
        
        # 预索引所有数据
        # base_map: {symbol: {ts: Bar}}
        base_map = {sym: {b.timestamp: b for b in bars} for sym, bars in self._base_data.items()}
        
        # others_map: {interval: {symbol: List[Bar]}} -> 已正序排列
        # 为了高效查找，可以使用已经排好序的列表进行二分查找，或者简单的缓存索引
        
        last_seen_other: Dict[str, Dict[str, Bar]] = {} # {interval: {symbol: Bar}}

        for ts in main_timeline:
            step_data = {}
            # 1. 基础周期数据（当前 Bar）
            base_slice = {}
            for sym in self._symbols:
                bar = base_map[sym].get(ts)
                if bar:
                    base_slice[sym] = bar
            
            step_data["base"] = base_slice if len(base_slice) > 1 else list(base_slice.values())[0] if base_slice else None
            
            # 2. 其他周期数据（已结束的最新 Bar）
            for interval, symbol_dict in self._other_data.items():
                if interval not in last_seen_other:
                    last_seen_other[interval] = {}
                
                interval_ms = INTERVAL_MS.get(interval, 0)
                
                for sym, bars in symbol_dict.items():
                    # 查找在该时间点 ts 之前已经"结束"的最新的 Bar
                    # 结束条件：bar.timestamp + interval_ms <= ts
                    # (由于 bars 是正序的，我们可以优化查找)
                    current_match = None
                    for b in bars:
                        if b.timestamp + interval_ms <= ts:
                            current_match = b
                        else:
                            break
                    
                    if current_match:
                        last_seen_other[interval][sym] = current_match
                
                if last_seen_other[interval]:
                    # 存入 step_data， key 格式如 "1h"
                    step_data[interval] = last_seen_other[interval].copy()

            self._aligned_data.append(step_data)

    @property
    def symbols(self) -> List[str]:
        return self._symbols

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self._aligned_data)

    def __len__(self) -> int:
        return len(self._aligned_data)


def create_feed(
    data: Union[List[Bar], Dict[str, List[Bar]]],
    symbol: str = None
) -> DataFeed:
    """工厂函数：根据输入数据自动创建 Feed
    
    Args:
        data: 单资产 List[Bar] 或多资产 Dict[symbol, List[Bar]]
        symbol: 单资产时的交易对名称
        
    Returns:
        SingleFeed 或 MultiFeed
    """
    if isinstance(data, list):
        return SingleFeed(data, symbol=symbol)
    elif isinstance(data, dict):
        # 检查是否是多周期嵌套格式 { "1m": {...}, "1h": {...} }
        # 如果是这种格式，创建 TimeframeAlignedFeed
        if any(k in INTERVAL_MS for k in data.keys()) and isinstance(list(data.values())[0], dict):
            # 找到基础频率（通常是最小的）
            intervals = sorted([k for k in data.keys() if k in INTERVAL_MS], key=lambda x: INTERVAL_MS[x])
            base_interval = intervals[0]
            base_data = data[base_interval]
            other_data = {itv: data[itv] for itv in intervals[1:]}
            return TimeframeAlignedFeed(base_data, other_data)
            
        feeds = {sym: SingleFeed(bars, symbol=sym) for sym, bars in data.items()}
        return MultiFeed(feeds)
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")
