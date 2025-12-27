# Phase 4 开发路线图：指标库生态完善

> **目标**: 将 PyQuantAlpha 技术指标覆盖率从 ~20% 提升至 100%，完全对齐 Backtrader 指标生态

---

## 📊 指标覆盖统计

| 状态 | 数量 | 说明 |
|------|------|------|
| ✅ 已实现 | 13 | PyQuantAlpha 当前指标 |
| 🔲 待实现 | **~80** | Backtrader 完整指标列表 |
| 📊 总计 | ~93 | 完全对齐后 |

---

## 📋 数据需求分析

### 输入数据类型

绝大多数指标只需要 **标准 K 线 OHLCV 数据**，无需额外数据源。

| 数据类型 | 字段 | 使用指标 |
|----------|------|----------|
| **Close** | `bar.close` | 大部分均线、振荡器、动量指标 |
| **High** | `bar.high` | Aroon, PSAR, Stochastic, ATR, ADX, Ichimoku |
| **Low** | `bar.low` | Aroon, PSAR, Stochastic, ATR, ADX, Ichimoku |
| **Volume** | `bar.volume` | OBV, VWMA, VolumeSlippage |
| **OHLC 全部** | `bar.*` | HeikinAshi, PivotPoint |

### 需要外部库依赖的指标 ⚠️

| 指标 | 外部依赖 | 说明 | 建议 |
|------|----------|------|------|
| **HurstExponent** | `numpy` | 线性拟合计算 | ✅ 已有依赖 |
| **OLS_Slope_Intercept** | `pandas`, `statsmodels` | 线性回归 | ⚠️ 可选实现 |
| **OLS_TransformationN** | `pandas`, `statsmodels` | 价差 Z-Score | ⚠️ 可选实现 |
| **OLS_BetaN** | `pandas` | Beta 计算 | ⚠️ 可选实现 |
| **CointN** | `pandas`, `statsmodels` | 协整检验 | ⚠️ 可选实现 |

> **建议**: OLS/Coint 类指标属于配对交易专用的统计套利指标，依赖 `statsmodels`。可标记为 **Phase 5 (高级统计)** 单独实现。

### 需要多数据源的指标 ⚠️

| 指标 | 数据需求 | 说明 |
|------|----------|------|
| **OLS_*** | 2 个 DataFeed | 计算两个资产的回归关系 |
| **CointN** | 2 个 DataFeed | 协整检验需要两个价格序列 |
| **Spread** | 2 个 DataFeed | 价差 = Asset1 - Asset2 × HedgeRatio |

> 这些指标依赖 PyQuantAlpha 的多资产回测功能 (`self.datas[0]`, `self.datas[1]`)，该功能已在 Phase 2 实现。

### 数据需求总结

| 类别 | 数量 | 数据需求 |
|------|------|----------|
| 仅需 Close | ~50 | 标准 |
| 需 High/Low | ~20 | 标准 |
| 需 Volume | ~5 | 标准 |
| 需 numpy | ~3 | ✅ 已有 |
| 需 statsmodels | ~4 | ⚠️ 可选 |
| 需多数据源 | ~4 | ✅ 已支持 |

## ✅ 已实现指标 (13 个)

| 类别 | 指标 | 来源文件 |
|------|------|----------|
| 均线 | SMA, EMA | `ma.py` |
| 振荡器 | RSI, MACD | `oscillator.py` |
| 动量 | Stochastic, Williams %R, CCI | `advanced.py` |
| 波动率 | ATR, Bollinger Bands | `volatility.py` |
| 趋势 | ADX, Ichimoku | `advanced.py` |
| 成交量 | OBV | `advanced.py` |
| 自定义 | SentimentDisparity | `advanced.py` |

---

## 🔲 待实现指标 (~80 个)

### Step 1: 基础运算与工具类 (basicops)

> 来源: `backtrader/indicators/basicops.py`

| 指标 | 别名 | 说明 |
|------|------|------|
| PeriodN | - | 周期基类 |
| Highest | MaxN | N 周期最高值 |
| Lowest | MinN | N 周期最低值 |
| SumN | - | N 周期求和 |
| AnyN | - | N 周期内任一为真 |
| AllN | - | N 周期内全部为真 |
| FindFirstIndexHighest | - | 最高值首次出现索引 |
| FindFirstIndexLowest | - | 最低值首次出现索引 |
| FindLastIndexHighest | - | 最高值最后出现索引 |
| FindLastIndexLowest | - | 最低值最后出现索引 |
| Accum | CumSum | 累积求和 |
| Average | Mean | 算术平均 |
| WeightedAverage | - | 加权平均 |
| ExponentialSmoothing | ExpSmoothing | 指数平滑 |

---

### Step 2: 移动平均线系列 (ma)

> 来源: `backtrader/indicators/sma.py`, `ema.py`, `wma.py`, `dema.py`, `hma.py`, `kama.py`, `zlema.py`, `smma.py`, `dma.py`

| 指标 | 全称 | 说明 |
|------|------|------|
| WMA | Weighted Moving Average | 加权移动平均 |
| DEMA | Double EMA | 双重指数移动平均 |
| TEMA | Triple EMA | 三重指数移动平均 |
| HMA | Hull Moving Average | 赫尔移动平均 |
| KAMA | Kaufman Adaptive MA | 考夫曼自适应均线 |
| ZLEMA | Zero Lag EMA | 零延迟指数均线 |
| SMMA | Smoothed MA | 平滑移动平均 |
| DMA | Dickson Moving Average | 迪克森移动平均 |
| T3 | Tillson T3 | 蒂尔森 T3 |
| VWMA | Volume Weighted MA | 成交量加权均线 |
| ALMA | Arnaud Legoux MA | 阿诺德勒格移动平均 |

---

### Step 3: 趋势指标

> 来源: `backtrader/indicators/aroon.py`, `psar.py`, `dpo.py`, `directionalmove.py`, `vortex.py`

| 指标 | 说明 |
|------|------|
| Aroon | 阿隆指标 (Up/Down/Oscillator) |
| AroonUp | 阿隆上升线 |
| AroonDown | 阿隆下降线 |
| AroonOscillator | 阿隆振荡器 |
| PSAR | Parabolic SAR |
| DPO | Detrended Price Oscillator |
| DirectionalMovement | 方向运动指标 |
| DirectionalMovementIndex | DMI |
| PlusDirectionalIndicator | +DI |
| MinusDirectionalIndicator | -DI |
| AverageDirectionalMovementIndex | ADMI |
| AverageDirectionalMovementIndexRating | ADXR |
| Vortex | 涡流指标 (VI+/VI-) |

---

### Step 4: 动量指标

> 来源: `backtrader/indicators/momentum.py`, `trix.py`, `tsi.py`, `ultimateoscillator.py`, `rmi.py`, `kst.py`, `lrsi.py`

| 指标 | 说明 |
|------|------|
| Momentum | 动量 = Close - Close[n] |
| MomentumOscillator | 动量振荡器 = 100 * (Close / Close[n]) |
| RateOfChange | ROC = (Close - Close[n]) / Close[n] |
| RateOfChange100 | ROC100 = ROC * 100 |
| TRIX | 三重 EMA 变化率 |
| TRIXSignal | TRIX 信号线 |
| TSI | True Strength Index |
| UltimateOscillator | 终极振荡器 |
| RMI | Relative Momentum Index |
| KST | Know Sure Thing |
| KSTSignal | KST 信号线 |
| LRSI | Laguerre RSI |

---

### Step 5: 振荡器

> 来源: `backtrader/indicators/oscillator.py`, `awesomeoscillator.py`, `accdecoscillator.py`, `prettygoodoscillator.py`, `priceoscillator.py`

| 指标 | 说明 |
|------|------|
| Oscillator | 基础振荡器 = data - indicator |
| SMAOscillator | SMA 振荡器 |
| EMAOscillator | EMA 振荡器 |
| WMAOscillator | WMA 振荡器 |
| DEMAOscillator | DEMA 振荡器 |
| AwesomeOscillator | AO |
| AccelerationDecelerationOscillator | AccDec |
| PrettyGoodOscillator | PGO |
| PriceOscillator | 价格振荡器 |
| PercentagePriceOscillator | PPO |

---

### Step 6: 波动率与通道

> 来源: `backtrader/indicators/atr.py`, `bollinger.py`, `deviation.py`, `envelope.py`

| 指标 | 说明 |
|------|------|
| TrueRange | TR |
| TrueHigh | 真实最高 |
| TrueLow | 真实最低 |
| AverageTrueRange | ATR (已实现) |
| StandardDeviation | StdDev |
| MeanDeviation | 均值偏差 |
| BollingerBands | BB (已实现) |
| BollingerBandsPct | BB% |
| Envelope | 包络线 (SMA ± %) |
| KeltnerChannel | 肯特纳通道 (EMA ± ATR) |
| DonchianChannel | 唐奇安通道 (N 日高低) |

---

### Step 7: 交叉与信号

> 来源: `backtrader/indicators/crossover.py`

| 指标 | 说明 |
|------|------|
| CrossOver | data0 上穿 data1 返回 1 |
| CrossDown | data0 下穿 data1 返回 1 |
| CrossUp | CrossOver 别名 |
| UpDay | 今日 > 昨日 |
| DownDay | 今日 < 昨日 |
| UpDayBool | UpDay 布尔版 |
| DownDayBool | DownDay 布尔版 |

---

### Step 8: 支撑阻力

> 来源: `backtrader/indicators/pivotpoint.py`

| 指标 | 说明 |
|------|------|
| PivotPoint | 轴心点 |
| FibonacciPivotPoint | 斐波那契轴心点 |
| DemarkPivotPoint | 德马克轴心点 |
| R1, R2, R3 | 阻力位 1/2/3 |
| S1, S2, S3 | 支撑位 1/2/3 |

---

### Step 9: 变化率与排名

> 来源: `backtrader/indicators/percentchange.py`, `percentrank.py`

| 指标 | 说明 |
|------|------|
| PercentChange | 百分比变化 |
| PercentRank | 百分位排名 |
| DV2 | David Varadi 2-period |

---

### Step 10: 特殊指标

> 来源: `backtrader/indicators/heikinashi.py`, `ichimoku.py`, `hurst.py`, `ols.py`, `hadelta.py`

| 指标 | 说明 |
|------|------|
| HeikinAshi | 平均足 K 线 |
| HeikinAshi_Open | HA 开盘价 |
| HeikinAshi_High | HA 最高价 |
| HeikinAshi_Low | HA 最低价 |
| HeikinAshi_Close | HA 收盘价 |
| Ichimoku | 一目均衡表 (已实现) |
| HurstExponent | 赫斯特指数 |
| OLS_Slope_InterceptN | 线性回归斜率/截距 |
| OLS_TransformationN | 线性回归转换 |
| OLS_BetaN | 线性回归 Beta |
| CointN | 协整检验 |
| HeikinAshiDelta | HA 涨跌 |

---

## 📁 文件结构规划

```
src/indicators/
├── __init__.py              # 更新导出列表
├── base.py                  # 基类 (已有)
├── ma.py                    # SMA, EMA (已有)
├── oscillator.py            # RSI, MACD (已有)
├── volatility.py            # ATR, BB (已有)
├── advanced.py              # ADX, Ichimoku, Stochastic... (已有)
│
├── basicops.py              # [NEW] Highest/Lowest/SumN/Accum/Average...
├── ma_extended.py           # [NEW] WMA/DEMA/TEMA/HMA/KAMA/ZLEMA/SMMA/DMA/T3
├── trend.py                 # [NEW] Aroon/PSAR/DPO/Vortex/DMI
├── momentum.py              # [NEW] Momentum/ROC/TRIX/TSI/UO/RMI/KST/LRSI
├── oscillators_extended.py  # [NEW] AO/AccDec/PGO/PPO
├── channel.py               # [NEW] Keltner/Donchian/Envelope
├── crossover.py             # [NEW] CrossOver/CrossDown/UpDay/DownDay
├── pivot.py                 # [NEW] PivotPoint/Fibonacci/Demark
├── percent.py               # [NEW] PercentChange/PercentRank/DV2
├── special.py               # [NEW] HeikinAshi/Hurst/OLS
└── deviation.py             # [NEW] StdDev/MeanDev
```

---

## 📅 开发计划

| Step | 内容 | 指标数 | 预估工时 |
|------|------|--------|----------|
| Step 1 | 基础运算工具 | ~14 | 2 天 |
| Step 2 | 均线系列 | ~11 | 2 天 |
| Step 3 | 趋势指标 | ~13 | 3 天 |
| Step 4 | 动量指标 | ~12 | 2 天 |
| Step 5 | 振荡器 | ~10 | 2 天 |
| Step 6 | 波动率与通道 | ~11 | 2 天 |
| Step 7 | 交叉信号 | ~7 | 1 天 |
| Step 8 | 支撑阻力 | ~7 | 1 天 |
| Step 9 | 变化率排名 | ~3 | 0.5 天 |
| Step 10 | 特殊指标 | ~11 | 2 天 |
| 测试 | 单元测试 + 集成 | - | 3 天 |
| 文档 | 更新文档 + Prompt | - | 2 天 |
| **合计** | | **~80+** | **22.5 天** |

---

## 🎯 验收标准

### 单元测试
- [ ] 每个指标至少 3 个测试用例
- [ ] 边界条件测试 (数据不足、极端值)
- [ ] 与 Backtrader 计算结果对比验证 (精度 < 0.0001)

### 文档
- [ ] `FINANCIAL_CONCEPTS.md` 新增所有指标说明
- [ ] 每个指标的 docstring 完整
- [ ] README 更新指标列表

### 集成
- [ ] `__init__.py` 导出所有新指标
- [ ] AI Prompt 更新可用指标列表
- [ ] 策略示例更新

---

## 🧪 Step 11: 单元测试

### 测试结构

```
tests/test_indicators/
├── test_basicops.py           # 基础运算测试
├── test_ma_extended.py        # 扩展均线测试
├── test_trend.py              # 趋势指标测试
├── test_momentum.py           # 动量指标测试
├── test_oscillators_extended.py  # 振荡器测试
├── test_channel.py            # 通道指标测试
├── test_crossover.py          # 交叉信号测试
├── test_pivot.py              # 支撑阻力测试
├── test_percent.py            # 变化率测试
└── test_special.py            # 特殊指标测试
```

### 测试模式

每个指标测试包含以下用例：

1. **正常计算测试**: 标准输入数据，验证输出正确性
2. **边界条件测试**: 数据不足时返回 `None`
3. **极端值测试**: 价格为 0、负数、超大值
4. **Backtrader 对比测试**: 使用相同数据，验证计算结果差异 < 0.0001

### 示例测试代码

```python
# tests/test_indicators/test_ma_extended.py
import pytest
from src.indicators import WMA, DEMA, TEMA, HMA, KAMA

class TestWMA:
    def test_basic_calculation(self):
        """测试 WMA 基本计算"""
        wma = WMA(period=5)
        prices = [10, 11, 12, 13, 14, 15]
        for p in prices:
            result = wma.update(p)
        assert result is not None
        assert abs(result - 13.67) < 0.01  # 预期值
    
    def test_insufficient_data(self):
        """数据不足时返回 None"""
        wma = WMA(period=10)
        for p in [10, 11, 12]:
            result = wma.update(p)
        assert result is None
    
    def test_backtrader_comparison(self):
        """与 Backtrader 计算结果对比"""
        # 测试数据和预期值来自 Backtrader 实际运行结果
        wma = WMA(period=5)
        test_data = [44, 45, 46, 47, 48, 49, 50]
        expected = 48.33  # Backtrader 计算结果
        for p in test_data:
            result = wma.update(p)
        assert abs(result - expected) < 0.0001
```

---

## 🔗 Step 12: 系统对接

### 12.1 指标注册到 `__init__.py`

```python
# src/indicators/__init__.py
from .ma_extended import WMA, DEMA, TEMA, HMA, KAMA, ZLEMA, SMMA, DMA, T3
from .trend import Aroon, AroonUp, AroonDown, AroonOscillator, PSAR, DPO, Vortex
from .momentum import Momentum, ROC, TRIX, TSI, UltimateOscillator, RMI, KST, LRSI
from .channel import KeltnerChannel, DonchianChannel, Envelope
from .crossover import CrossOver, CrossDown, UpDay, DownDay
from .pivot import PivotPoint, FibonacciPivotPoint, DemarkPivotPoint
# ... 更多导入

__all__ = [
    # 现有指标
    "SMA", "EMA", "RSI", "MACD", "ATR", "BollingerBands",
    "ADX", "Ichimoku", "Stochastic", "WilliamsR", "CCI", "OBV",
    # 新增均线
    "WMA", "DEMA", "TEMA", "HMA", "KAMA", "ZLEMA", "SMMA", "DMA", "T3",
    # 新增趋势
    "Aroon", "AroonUp", "AroonDown", "AroonOscillator", "PSAR", "DPO", "Vortex",
    # 新增动量
    "Momentum", "ROC", "TRIX", "TSI", "UltimateOscillator", "RMI", "KST", "LRSI",
    # 新增通道
    "KeltnerChannel", "DonchianChannel", "Envelope",
    # 新增交叉
    "CrossOver", "CrossDown", "UpDay", "DownDay",
    # 新增支撑阻力
    "PivotPoint", "FibonacciPivotPoint", "DemarkPivotPoint",
    # ... 更多
]
```

### 12.2 策略基类集成

确保所有指标可在策略的 `init()` 中直接使用：

```python
# 用户策略示例
class MyStrategy(BaseStrategy):
    def init(self):
        self.kama = KAMA(period=10)
        self.aroon = Aroon(period=25)
        self.keltner = KeltnerChannel(period=20, atr_mult=2.0)
    
    def on_bar(self):
        kama_val = self.kama.update(self.bar.close)
        aroon_result = self.aroon.update(self.bar.high, self.bar.low)
        kc = self.keltner.update(self.bar.high, self.bar.low, self.bar.close)
```

---

## 🤖 Step 13: AI Prompt 更新

### 13.1 更新 `src/ai/prompt.py`

在 `SYSTEM_PROMPT` 中添加新指标的说明：

```python
INDICATOR_DOCS = """
## 可用技术指标

### 均线类 (Moving Averages)
| 指标 | 参数 | 输入 | 输出 | 说明 |
|------|------|------|------|------|
| SMA(period) | period: int | close | float | 简单移动平均 |
| EMA(period) | period: int | close | float | 指数移动平均 |
| WMA(period) | period: int | close | float | 加权移动平均 |
| DEMA(period) | period: int | close | float | 双重指数平均 |
| TEMA(period) | period: int | close | float | 三重指数平均 |
| HMA(period) | period: int | close | float | 赫尔移动平均 |
| KAMA(period, fast, slow) | period, fast, slow: int | close | float | 考夫曼自适应 |

### 趋势类 (Trend)
| 指标 | 参数 | 输入 | 输出 | 说明 |
|------|------|------|------|------|
| Aroon(period) | period: int | high, low | AroonResult(up, down, osc) | 阿隆指标 |
| PSAR(af, afmax) | af, afmax: float | high, low, close | float | 抛物线止损 |
| ADX(period) | period: int | high, low, close | float | 平均趋向指标 |

### 动量类 (Momentum)
| 指标 | 参数 | 输入 | 输出 | 说明 |
|------|------|------|------|------|
| Momentum(period) | period: int | close | float | 动量 = close - close[n] |
| ROC(period) | period: int | close | float | 变化率 |
| TRIX(period) | period: int | close | float | 三重 EMA 变化率 |
| TSI(r, s) | r, s: int | close | float | 真实强度指数 |
| KST(...) | 多周期参数 | close | float | Know Sure Thing |

### 通道类 (Channel)
| 指标 | 参数 | 输入 | 输出 | 说明 |
|------|------|------|------|------|
| KeltnerChannel(period, mult) | period, mult: int/float | high, low, close | KCResult(mid, upper, lower) | 肯特纳通道 |
| DonchianChannel(period) | period: int | high, low | DCResult(upper, lower, mid) | 唐奇安通道 |
| Envelope(period, pct) | period, pct: int/float | close | EnvResult(upper, lower) | 包络线 |

### 振荡器类 (Oscillator)
| 指标 | 参数 | 输入 | 输出 | 说明 |
|------|------|------|------|------|
| RSI(period) | period: int | close | float (0-100) | 相对强弱 |
| Stochastic(k, d) | k, d: int | high, low, close | StochResult(k, d) | 随机指标 |
| CCI(period) | period: int | high, low, close | float | 顺势指标 |
| UltimateOscillator(p1, p2, p3) | p1, p2, p3: int | high, low, close | float | 终极振荡器 |

### 交叉信号 (Crossover)
| 指标 | 参数 | 输入 | 输出 | 说明 |
|------|------|------|------|------|
| CrossOver() | - | v1, v2 | bool | v1 上穿 v2 |
| CrossDown() | - | v1, v2 | bool | v1 下穿 v2 |
"""
```

### 13.2 更新策略生成示例

在 Prompt 中添加使用新指标的策略示例：

```python
STRATEGY_EXAMPLES = """
## 策略示例

### 示例 1: KAMA + Keltner 通道策略
```python
class KAMAKeltnerStrategy(BaseStrategy):
    def init(self):
        self.kama = KAMA(period=10)
        self.keltner = KeltnerChannel(period=20, atr_mult=2.0)
    
    def on_bar(self):
        kama = self.kama.update(self.bar.close)
        kc = self.keltner.update(self.bar.high, self.bar.low, self.bar.close)
        
        if kama and kc:
            # 价格突破上轨且 KAMA 上升，买入
            if self.bar.close > kc.upper and kama > self.kama.prev:
                self.order("BTCUSDT", "BUY", 0.1)
            # 价格跌破下轨，卖出
            elif self.bar.close < kc.lower:
                self.close("BTCUSDT")
```

### 示例 2: TSI + PSAR 动量策略
```python
class TSIPSARStrategy(BaseStrategy):
    def init(self):
        self.tsi = TSI(r=25, s=13)
        self.psar = PSAR(af=0.02, afmax=0.2)
    
    def on_bar(self):
        tsi = self.tsi.update(self.bar.close)
        psar = self.psar.update(self.bar.high, self.bar.low, self.bar.close)
        
        if tsi and psar:
            # TSI > 0 且价格在 PSAR 上方，做多
            if tsi > 0 and self.bar.close > psar:
                self.order("BTCUSDT", "BUY", 0.1)
            # TSI < 0 且价格在 PSAR 下方，平仓
            elif tsi < 0 and self.bar.close < psar:
                self.close("BTCUSDT")
```
"""
```

---

## 📋 Step 14: 文档更新

### 14.1 更新 `FINANCIAL_CONCEPTS.md`

为每个新指标添加说明：
- 指标名称和别名
- 计算公式
- 参数说明
- 用法和交易信号

### 14.2 更新 `CODE_QUALITY_REPORT.md`

- 更新指标总数
- 更新测试覆盖率
- 记录 Phase 4 完成状态

### 14.3 更新 `BACKTRADER_COMPARISON_REPORT.md`

- 技术指标覆盖率: 80% → 100%
- 更新对比表格

---

## 📅 完整开发计划

| Step | 内容 | 指标数 | 预估工时 |
|------|------|--------|----------|
| Step 1 | 基础运算工具 | ~14 | 2 天 |
| Step 2 | 均线系列 | ~11 | 2 天 |
| Step 3 | 趋势指标 | ~13 | 3 天 |
| Step 4 | 动量指标 | ~12 | 2 天 |
| Step 5 | 振荡器 | ~10 | 2 天 |
| Step 6 | 波动率与通道 | ~11 | 2 天 |
| Step 7 | 交叉信号 | ~7 | 1 天 |
| Step 8 | 支撑阻力 | ~7 | 1 天 |
| Step 9 | 变化率排名 | ~3 | 0.5 天 |
| Step 10 | 特殊指标 | ~11 | 2 天 |
| **Step 11** | **单元测试** | - | **3 天** |
| **Step 12** | **系统对接** | - | **1 天** |
| **Step 13** | **AI Prompt 更新** | - | **1 天** |
| **Step 14** | **文档更新** | - | **1 天** |
| **合计** | | **~80+** | **23.5 天** |

---

## ✅ 最终验收清单

### 代码层面
- [ ] 所有 ~80 个新指标实现完成
- [ ] 单元测试覆盖率 > 90%
- [ ] 与 Backtrader 计算结果对比验证通过
- [ ] 无 lint 警告

### 集成层面
- [ ] `__init__.py` 导出所有新指标
- [ ] 策略基类可正常使用新指标
- [ ] AI 可生成使用新指标的策略

### 文档层面
- [ ] `FINANCIAL_CONCEPTS.md` 完整更新
- [ ] `BACKTRADER_COMPARISON_REPORT.md` 更新
- [ ] `CODE_QUALITY_REPORT.md` 更新
- [ ] README 指标列表更新

### 验收测试
- [ ] 运行 `pytest tests/test_indicators/ -v` 全部通过
- [ ] 使用自然语言让 AI 生成包含新指标的策略
- [ ] 回测包含新指标的策略，结果正确

---

## 🔗 参考资源

- [Backtrader Indicators 源码](https://github.com/mementum/backtrader/tree/master/backtrader/indicators)
- [TA-Lib 文档](https://ta-lib.org/function.html)
- [Investopedia 技术分析](https://www.investopedia.com/technical-analysis-4689657)
- [TradingView 指标参考](https://www.tradingview.com/support/solutions/43000502338-indicators/)
