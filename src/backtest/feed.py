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
from typing import Dict, Iterator, List, Optional, Union

from src.data.models import Bar


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
        
    Example:
        >>> feed = create_feed(btc_bars, symbol="BTCUSDT")  # 单资产
        >>> feed = create_feed({"BTCUSDT": btc_bars, "ETHUSDT": eth_bars})  # 多资产
    """
    if isinstance(data, list):
        return SingleFeed(data, symbol=symbol)
    elif isinstance(data, dict):
        feeds = {sym: SingleFeed(bars, symbol=sym) for sym, bars in data.items()}
        return MultiFeed(feeds)
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")
