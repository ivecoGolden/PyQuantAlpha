# Phase 3.5: 辅助数据流集成 (AuxDataFeed)

> **目标**：将资金费率、市场情绪等辅助数据作为"数据流"注入回测引擎，让策略像读取价格数据一样读取辅助数据，无需手动调用 API。

---

## 🎯 核心问题

当前架构中，策略通过 `self.get_funding_rates()` 主动调用 API 获取辅助数据。这导致：

1. **时间错位**：`init()` 调用时引擎时钟为 0，获取的是实时数据而非回测时点数据
2. **静态使用**：用户通常只在 `init()` 获取一次，整个回测使用静态值
3. **性能问题**：每次调用都可能触发网络请求
4. **逻辑复杂**：AI 生成的策略需要管理刷新逻辑

---

## 🏗️ 目标架构

```
┌─────────────────────────────────────────────────────────┐
│                    BacktestEngine                       │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐                   │
│  │  PriceFeed   │    │ AuxDataFeed  │  ← 新增           │
│  │  (K线数据)   │    │ (资金费率等) │                   │
│  └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                           │
│         ▼                   ▼                           │
│  ┌──────────────────────────────────────┐               │
│  │         DataAligner (时间戳对齐)      │  ← 新增       │
│  └──────────────────────────────────────┘               │
│                      │                                  │
│                      ▼                                  │
│            on_bar(data: AlignedData)                    │
│            data.bar / data.funding_rate                 │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 实现步骤

### Step 1: 定义 AuxDataFeed 抽象类 [0.5 天]

#### [NEW] `src/backtest/aux_feed.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Any
from dataclasses import dataclass

@dataclass
class AuxDataPoint:
    """辅助数据点"""
    timestamp: int
    value: Any

class AuxDataFeed(ABC):
    """辅助数据流抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """数据流名称，如 'funding_rate'"""
        pass
    
    @abstractmethod
    def preload(self, start_time: int, end_time: int) -> None:
        """预加载指定时间范围的数据"""
        pass
    
    @abstractmethod
    def get_value_at(self, timestamp: int) -> Optional[Any]:
        """获取指定时间点的值（最近的已结算数据）"""
        pass
```

---

### Step 2: 实现 FundingRateFeed [1 天]

#### [NEW] `src/backtest/feeds/funding_rate_feed.py`

```python
class FundingRateFeed(AuxDataFeed):
    """资金费率数据流"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self._data: List[FundingRateData] = []
    
    @property
    def name(self) -> str:
        return "funding_rate"
    
    def preload(self, start_time: int, end_time: int) -> None:
        """从数据库/API 预加载资金费率"""
        # 使用 Repository 获取数据
        import asyncio
        from src.data.repository import MarketDataRepository
        repo = MarketDataRepository()
        self._data = asyncio.run(repo.get_funding_rates(
            self.symbol, start_time, end_time
        ))
    
    def get_value_at(self, timestamp: int) -> Optional[float]:
        """获取指定时间点之前最近的资金费率"""
        # 二分查找最近的已结算费率
        for item in reversed(self._data):
            if item.timestamp <= timestamp:
                return item.funding_rate
        return None
```

---

### Step 3: 定义 AlignedData 结构 [0.5 天]

#### [MODIFY] `src/backtest/models.py`

```python
@dataclass
class AlignedData:
    """对齐后的数据结构"""
    bar: Bar                           # 主数据（K线）
    aux: Dict[str, Any] = field(default_factory=dict)  # 辅助数据
    
    @property
    def funding_rate(self) -> Optional[float]:
        return self.aux.get("funding_rate")
    
    @property
    def sentiment(self) -> Optional[float]:
        return self.aux.get("sentiment")
```

---

### Step 4: 引擎集成 AuxDataFeed [1 天]

#### [MODIFY] `src/backtest/engine.py`

主要改动：

1. **初始化时注册辅助数据流**
```python
def __init__(self, ...):
    self._aux_feeds: List[AuxDataFeed] = []

def add_aux_feed(self, feed: AuxDataFeed) -> "BacktestEngine":
    """注册辅助数据流（链式调用）"""
    self._aux_feeds.append(feed)
    return self
```

2. **回测开始前预加载**
```python
def run(self, ...):
    # 获取数据时间范围
    start_ts = feed.start_time
    end_ts = feed.end_time
    
    # 预加载所有辅助数据
    for aux_feed in self._aux_feeds:
        aux_feed.preload(start_ts, end_ts)
```

3. **遍历时对齐数据**
```python
for bar in feed:
    # 构建对齐数据
    aux_values = {}
    for aux_feed in self._aux_feeds:
        aux_values[aux_feed.name] = aux_feed.get_value_at(bar.timestamp)
    
    aligned_data = AlignedData(bar=bar, aux=aux_values)
    strategy.on_bar(aligned_data)
```

---

### Step 5: 更新 AI Prompt [0.5 天]

#### [MODIFY] `src/ai/prompt.py`

新增辅助数据使用说明：

```python
## 辅助数据访问

回测引擎会自动对齐辅助数据，策略可直接读取：

```python
def on_bar(self, data):
    bar = data.bar  # K线数据
    funding_rate = data.funding_rate  # 资金费率（自动对齐）
    sentiment = data.sentiment  # 市场情绪（自动对齐）
    
    if funding_rate and funding_rate < -0.0001:
        self.order("BTCUSDT", "BUY", 0.1)
```

**注意**：辅助数据需要在回测配置中启用。
```

---

### Step 6: API 层集成 [0.5 天]

#### [MODIFY] `src/api/main.py`

回测接口支持辅助数据配置：

```python
@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    engine = BacktestEngine(config)
    
    # 根据配置添加辅助数据流
    if request.enable_funding_rate:
        engine.add_aux_feed(FundingRateFeed(request.symbol))
    if request.enable_sentiment:
        engine.add_aux_feed(SentimentFeed(request.symbol))
    
    return engine.run(strategy_code, bars)
```

---

## 📁 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| NEW | `src/backtest/aux_feed.py` | AuxDataFeed 抽象类 |
| NEW | `src/backtest/feeds/__init__.py` | Feeds 子模块 |
| NEW | `src/backtest/feeds/funding_rate_feed.py` | 资金费率 Feed |
| NEW | `src/backtest/feeds/sentiment_feed.py` | 市场情绪 Feed |
| MODIFY | `src/backtest/models.py` | 新增 AlignedData |
| MODIFY | `src/backtest/engine.py` | 集成 AuxDataFeed |
| MODIFY | `src/ai/prompt.py` | 更新使用说明 |
| MODIFY | `src/api/main.py` | API 层配置支持 |
| NEW | `tests/test_backtest/test_aux_feed.py` | 单元测试 |

---

## 🧪 Step 7: 单元测试 [0.5 天]

#### [NEW] `tests/test_backtest/test_aux_feed.py`

```python
import pytest
from src.backtest.aux_feed import AuxDataFeed, AuxDataPoint
from src.backtest.feeds.funding_rate_feed import FundingRateFeed

class TestAuxDataFeed:
    """AuxDataFeed 抽象类测试"""
    
    def test_funding_rate_feed_preload(self):
        """测试资金费率预加载"""
        feed = FundingRateFeed("BTCUSDT")
        # 使用 mock 数据
        feed._data = [
            AuxDataPoint(timestamp=1000, value=0.0001),
            AuxDataPoint(timestamp=2000, value=-0.0002),
            AuxDataPoint(timestamp=3000, value=0.0003),
        ]
        
        assert feed.get_value_at(1500) == 0.0001  # 返回最近的已结算值
        assert feed.get_value_at(2500) == -0.0002
        assert feed.get_value_at(500) is None  # 无数据
    
    def test_no_future_data(self):
        """验证不会偷看未来数据"""
        feed = FundingRateFeed("BTCUSDT")
        feed._data = [
            AuxDataPoint(timestamp=1000, value=0.0001),
            AuxDataPoint(timestamp=2000, value=0.0005),
        ]
        
        # 时间戳 1500 只能看到 1000 的数据，不能看到 2000
        assert feed.get_value_at(1500) == 0.0001
```

---

## 🧪 Step 8: 集成测试 [0.5 天]

#### [NEW] `tests/test_backtest/test_aligned_data_integration.py`

```python
import pytest
from src.backtest.engine import BacktestEngine
from src.backtest.feeds.funding_rate_feed import FundingRateFeed
from src.data.models import Bar

class TestAlignedDataIntegration:
    """AlignedData 集成测试"""
    
    def test_strategy_receives_aligned_data(self):
        """策略能正确接收对齐后的数据"""
        received_data = []
        
        strategy_code = '''
class Strategy:
    def init(self):
        pass
    
    def on_bar(self, data):
        # 验证 data 结构
        assert hasattr(data, 'bar')
        assert hasattr(data, 'funding_rate')
'''
        
        bars = [
            Bar(timestamp=1000, open=100, high=101, low=99, close=100.5, volume=1000),
            Bar(timestamp=2000, open=100.5, high=102, low=100, close=101, volume=1200),
        ]
        
        engine = BacktestEngine()
        feed = FundingRateFeed("BTCUSDT")
        feed._data = [AuxDataPoint(timestamp=500, value=0.0001)]
        engine.add_aux_feed(feed)
        
        result = engine.run(strategy_code, bars)
        assert result is not None
    
    def test_funding_rate_triggers_trade(self):
        """资金费率能正确触发交易"""
        strategy_code = '''
class Strategy:
    def init(self):
        pass
    
    def on_bar(self, data):
        if data.funding_rate and data.funding_rate < -0.0001:
            self.order("BTCUSDT", "BUY", 0.1)
'''
        
        bars = [Bar(timestamp=i*1000, open=100, high=101, low=99, close=100, volume=1000) for i in range(10)]
        
        engine = BacktestEngine()
        feed = FundingRateFeed("BTCUSDT")
        feed._data = [AuxDataPoint(timestamp=0, value=-0.0005)]  # 负费率
        engine.add_aux_feed(feed)
        
        result = engine.run(strategy_code, bars)
        assert len(result.trades) > 0  # 应该有交易
```

---

## 🧪 Step 9: 端到端测试 [0.5 天]

#### [NEW] `tests/manual/test_e2e_aux_feed.py`

```python
"""
端到端测试：验证完整的辅助数据流程

运行方式：
    pytest tests/manual/test_e2e_aux_feed.py -v
"""

import pytest
from src.backtest.engine import BacktestEngine
from src.backtest.feeds.funding_rate_feed import FundingRateFeed
from src.backtest.feeds.sentiment_feed import SentimentFeed
from src.data.binance import BinanceClient

class TestE2EAuxFeed:
    """端到端辅助数据流测试"""
    
    @pytest.mark.slow
    def test_real_funding_rate_backtest(self):
        """使用真实资金费率数据回测"""
        strategy_code = '''
class Strategy:
    def init(self):
        pass
    
    def on_bar(self, data):
        bar = data.bar
        fr = data.funding_rate
        
        if fr is not None:
            if fr < -0.0001:
                self.order("BTCUSDT", "BUY", 0.1)
            elif fr > 0.0003:
                self.close("BTCUSDT")
'''
        
        # 获取真实 K 线数据
        client = BinanceClient()
        bars = client.get_klines("BTCUSDT", "1h", limit=100)
        
        # 配置引擎
        engine = BacktestEngine()
        engine.add_aux_feed(FundingRateFeed("BTCUSDT"))
        
        result = engine.run(strategy_code, bars)
        
        print(f"总收益率: {result.total_return:.2%}")
        print(f"交易次数: {len(result.trades)}")
        
        assert result is not None
```

---

## 📁 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| NEW | `src/backtest/aux_feed.py` | AuxDataFeed 抽象类 |
| NEW | `src/backtest/feeds/__init__.py` | Feeds 子模块 |
| NEW | `src/backtest/feeds/funding_rate_feed.py` | 资金费率 Feed |
| NEW | `src/backtest/feeds/sentiment_feed.py` | 市场情绪 Feed |
| MODIFY | `src/backtest/models.py` | 新增 AlignedData |
| MODIFY | `src/backtest/engine.py` | 集成 AuxDataFeed |
| MODIFY | `src/ai/prompt.py` | 更新使用说明 |
| MODIFY | `src/api/main.py` | API 层配置支持 |
| DELETE | 策略中的 `get_funding_rates()` | 移除旧 API |
| DELETE | 策略中的 `get_sentiment()` | 移除旧 API |
| NEW | `tests/test_backtest/test_aux_feed.py` | 单元测试 |
| NEW | `tests/test_backtest/test_aligned_data_integration.py` | 集成测试 |
| NEW | `tests/manual/test_e2e_aux_feed.py` | 端到端测试 |

---

## ⏱️ 工时估算

| Step | 内容 | 工时 |
|------|------|------|
| 1 | AuxDataFeed 抽象类 | 0.5 天 |
| 2 | FundingRateFeed 实现 | 1 天 |
| 3 | AlignedData 结构 | 0.5 天 |
| 4 | 引擎集成 | 1 天 |
| 5 | Prompt 更新 | 0.5 天 |
| 6 | API 集成 | 0.5 天 |
| 7 | 单元测试 | 0.5 天 |
| 8 | 集成测试 | 0.5 天 |
| 9 | 端到端测试 | 0.5 天 |
| **总计** | | **5.5 天** |

---

## ✅ 验收标准

1. [ ] 策略可通过 `data.funding_rate` 直接读取资金费率
2. [ ] 策略可通过 `data.sentiment` 直接读取市场情绪
3. [ ] 辅助数据与 K 线时间戳正确对齐（不偷看未来）
4. [ ] 回测速度无明显下降（预加载 vs 实时调用）
5. [ ] AI 生成的策略能正确使用新语法
6. [ ] 单元测试覆盖率 > 90%
7. [ ] 集成测试全部通过
8. [ ] 端到端测试验证完整流程
9. [ ] 移除旧 API（`get_funding_rates`, `get_sentiment`）
