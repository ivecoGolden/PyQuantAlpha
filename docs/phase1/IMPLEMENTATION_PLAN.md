# PyQuantAlpha Phase 1 实施计划

> **阶段目标**: AI 生成策略 → 自研回测引擎 → 前端测试页面

---

## 1. 技术选型

| 模块 | 技术选择 | 说明 |
|------|---------|------|
| AI 模型 | DeepSeek | 性价比高，代码生成能力强 |
| 回测引擎 | 自研 | 完全可控，可定制优化 |
| 数据源 | Binance API | 官方接口，数据权威 |
| 前端 | Streamlit | 快速原型 |
| 后端 | FastAPI | 异步 API 服务 |

---

## 2. 项目结构

```
PyQuantAlpha/
├── docs/                    # 项目文档
│   ├── ARCHITECTURE.md
│   ├── FEASIBILITY_REPORT.md
│   └── IMPLEMENTATION_PLAN.md
├── src/
│   ├── api/                 # API 服务
│   │   ├── __init__.py
│   │   └── main.py          # FastAPI 入口
│   ├── ai/                  # AI 策略生成
│   │   ├── __init__.py
│   │   ├── deepseek.py      # DeepSeek API 封装
│   │   ├── prompt.py        # Prompt 模板
│   │   └── validator.py     # 代码校验
│   ├── backtest/            # 回测引擎
│   │   ├── __init__.py
│   │   ├── engine.py        # 回测核心
│   │   ├── order.py         # 订单管理
│   │   ├── position.py      # 持仓管理
│   │   └── analyzer.py      # 绩效分析
│   ├── data/                # 数据层
│   │   ├── __init__.py
│   │   ├── binance.py       # Binance API
│   │   └── models.py        # 数据模型
│   ├── indicators/          # 技术指标
│   │   ├── __init__.py
│   │   ├── ma.py            # 移动平均
│   │   ├── rsi.py           # RSI
│   │   └── macd.py          # MACD
│   └── strategy/            # 策略基类
│       ├── __init__.py
│       └── base.py
├── frontend/                # 前端
│   └── app.py               # Streamlit 入口
├── tests/                   # 测试
├── requirements.txt
└── README.md
```

---

## 3. 模块详细设计

### 3.1 数据层 (data/)

#### Binance API 封装

```python
# src/data/binance.py
import requests
from typing import List
from datetime import datetime

class BinanceClient:
    BASE_URL = "https://api.binance.com/api/v3"
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str, 
        start_time: int = None,
        end_time: int = None,
        limit: int = 1000
    ) -> List[dict]:
        """获取 K 线数据"""
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
            
        response = requests.get(f"{self.BASE_URL}/klines", params=params)
        response.raise_for_status()
        return self._parse_klines(response.json())
    
    def _parse_klines(self, raw_data: list) -> List[dict]:
        return [
            {
                "timestamp": item[0],
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5])
            }
            for item in raw_data
        ]
```

#### 数据模型

```python
# src/data/models.py
from dataclasses import dataclass

@dataclass
class Bar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
```

---

### 3.2 技术指标 (indicators/)

```python
# src/indicators/ma.py
from typing import List

class EMA:
    def __init__(self, period: int):
        self.period = period
        self.values = []
        self.alpha = 2 / (period + 1)
        self._value = None
    
    def update(self, price: float) -> float:
        if self._value is None:
            self._value = price
        else:
            self._value = self.alpha * price + (1 - self.alpha) * self._value
        self.values.append(self._value)
        return self._value
    
    @property
    def value(self) -> float:
        return self._value

class SMA:
    def __init__(self, period: int):
        self.period = period
        self.prices = []
        self._value = None
    
    def update(self, price: float) -> float:
        self.prices.append(price)
        if len(self.prices) > self.period:
            self.prices.pop(0)
        self._value = sum(self.prices) / len(self.prices)
        return self._value
    
    @property
    def value(self) -> float:
        return self._value
```

---

### 3.3 回测引擎 (backtest/)

#### 订单管理

```python
# src/backtest/order.py
from dataclasses import dataclass
from enum import Enum

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    id: int
    symbol: str
    side: OrderSide
    size: float
    price: float = None  # None 表示市价单
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = None
    filled_time: int = None
```

#### 持仓管理

```python
# src/backtest/position.py
from dataclasses import dataclass

@dataclass
class Position:
    symbol: str
    size: float = 0
    avg_price: float = 0
    
    def update(self, size: float, price: float):
        if self.size == 0:
            self.avg_price = price
        elif (self.size > 0 and size > 0) or (self.size < 0 and size < 0):
            # 同向加仓
            total_cost = self.avg_price * abs(self.size) + price * abs(size)
            self.avg_price = total_cost / (abs(self.size) + abs(size))
        self.size += size
        
        if abs(self.size) < 1e-8:
            self.size = 0
            self.avg_price = 0
    
    @property
    def unrealized_pnl(self, current_price: float) -> float:
        return (current_price - self.avg_price) * self.size
```

#### 回测核心

```python
# src/backtest/engine.py
from typing import List, Type
from dataclasses import dataclass, field

@dataclass
class BacktestConfig:
    initial_capital: float = 10000
    commission_rate: float = 0.001  # 0.1%
    slippage: float = 0.0005        # 0.05%

@dataclass
class BacktestResult:
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    equity_curve: List[float]
    trades: List[dict]

class BacktestEngine:
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.capital = self.config.initial_capital
        self.positions = {}
        self.pending_orders = []
        self.trades = []
        self.equity_curve = []
        self._order_id = 0
    
    def run(self, strategy, data: List[Bar]) -> BacktestResult:
        # 注入交易方法
        strategy.order = self._create_order
        strategy.close = self._close_position
        strategy.get_position = self._get_position
        strategy.equity = self.capital
        
        strategy.init()
        
        for bar in data:
            # 更新持仓盈亏
            self._update_positions(bar)
            # 执行待处理订单
            self._process_orders(bar)
            # 调用策略
            strategy.on_bar(bar)
            # 记录净值
            self.equity_curve.append(self._calculate_equity(bar))
        
        return self._calculate_results()
    
    def _create_order(self, symbol: str, side: str, size: float):
        order = Order(
            id=self._order_id,
            symbol=symbol,
            side=OrderSide(side),
            size=size
        )
        self._order_id += 1
        self.pending_orders.append(order)
        return order
    
    def _process_orders(self, bar: Bar):
        for order in self.pending_orders:
            # 模拟成交：使用收盘价 + 滑点
            fill_price = bar.close * (1 + self.config.slippage)
            if order.side == OrderSide.SELL:
                fill_price = bar.close * (1 - self.config.slippage)
            
            # 计算手续费
            commission = fill_price * order.size * self.config.commission_rate
            
            # 更新资金
            if order.side == OrderSide.BUY:
                cost = fill_price * order.size + commission
                if cost > self.capital:
                    continue  # 资金不足
                self.capital -= cost
            else:
                proceeds = fill_price * order.size - commission
                self.capital += proceeds
            
            # 更新持仓
            position = self.positions.setdefault(order.symbol, Position(order.symbol))
            delta = order.size if order.side == OrderSide.BUY else -order.size
            position.update(delta, fill_price)
            
            # 记录成交
            order.status = OrderStatus.FILLED
            order.filled_price = fill_price
            order.filled_time = bar.timestamp
            self.trades.append(order)
        
        self.pending_orders = []
```

---

### 3.4 AI 策略生成 (ai/)

#### DeepSeek 封装

```python
# src/ai/deepseek.py
import openai

class DeepSeekClient:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
    
    def generate_strategy(self, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="deepseek-coder",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
```

#### Prompt 模板

```python
# src/ai/prompt.py
SYSTEM_PROMPT = """
你是一个量化交易策略开发助手。根据用户的自然语言描述，生成 Python 策略代码。

策略代码必须遵循以下格式：

```python
class Strategy:
    def init(self):
        # 初始化指标
        self.ema20 = EMA(20)
        self.ema60 = EMA(60)
    
    def on_bar(self, bar):
        # 更新指标
        self.ema20.update(bar.close)
        self.ema60.update(bar.close)
        
        # 交易逻辑
        if 条件:
            self.order("BTCUSDT", "BUY", 0.1)
        
        if 条件:
            self.close("BTCUSDT")
```

可用的指标：EMA, SMA, RSI, MACD
可用的方法：
- self.order(symbol, side, size): 下单，side 为 "BUY" 或 "SELL"
- self.close(symbol): 平仓
- self.get_position(symbol): 获取持仓

只输出代码，不要解释。
"""
```

#### 代码校验

```python
# src/ai/validator.py
import ast

ALLOWED_NAMES = {
    'EMA', 'SMA', 'RSI', 'MACD',
    'Strategy', 'self', 'bar',
    'order', 'close', 'get_position',
    'True', 'False', 'None',
    'and', 'or', 'not',
    'print', 'len', 'range', 'abs', 'max', 'min'
}

def validate_strategy_code(code: str) -> tuple[bool, str]:
    """验证策略代码安全性"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    
    # 检查是否只有一个类定义
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    if len(classes) != 1 or classes[0].name != 'Strategy':
        return False, "必须定义一个名为 Strategy 的类"
    
    # 检查不允许的调用
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            return False, "不允许 import 语句"
        if isinstance(node, ast.ImportFrom):
            return False, "不允许 from ... import 语句"
    
    return True, "验证通过"
```

---

### 3.5 API 服务 (api/)

```python
# src/api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="PyQuantAlpha API")

class GenerateRequest(BaseModel):
    prompt: str

class BacktestRequest(BaseModel):
    code: str
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    days: int = 30

@app.post("/api/generate")
async def generate_strategy(req: GenerateRequest):
    code = deepseek_client.generate_strategy(req.prompt)
    valid, msg = validate_strategy_code(code)
    if not valid:
        raise HTTPException(400, msg)
    return {"code": code}

@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    # 获取数据
    data = binance_client.get_klines(req.symbol, req.interval, limit=req.days*24)
    
    # 执行策略代码
    strategy = execute_strategy_code(req.code)
    
    # 运行回测
    engine = BacktestEngine()
    result = engine.run(strategy, data)
    
    return result
```

---

### 3.6 前端 (frontend/)

```python
# frontend/app.py
import streamlit as st
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="PyQuantAlpha", layout="wide")
st.title("🚀 PyQuantAlpha - AI 量化策略平台")

# 策略输入
st.header("1️⃣ 描述你的策略")
prompt = st.text_area(
    "用自然语言描述你的交易策略：",
    placeholder="例如：用 EMA20 上穿 EMA60 做多 BTC，下穿时平仓，止损 2%",
    height=100
)

if st.button("🧠 生成策略"):
    with st.spinner("AI 正在生成策略..."):
        response = requests.post(
            "http://localhost:8000/api/generate",
            json={"prompt": prompt}
        )
        if response.ok:
            st.session_state.code = response.json()["code"]

# 代码预览
if "code" in st.session_state:
    st.header("2️⃣ 策略代码")
    code = st.text_area("编辑代码：", st.session_state.code, height=300)
    
    col1, col2, col3 = st.columns(3)
    symbol = col1.selectbox("交易对", ["BTCUSDT", "ETHUSDT", "BNBUSDT"])
    interval = col2.selectbox("周期", ["1h", "4h", "1d"])
    days = col3.slider("回测天数", 7, 365, 30)
    
    if st.button("📊 运行回测"):
        with st.spinner("回测中..."):
            response = requests.post(
                "http://localhost:8000/api/backtest",
                json={"code": code, "symbol": symbol, "interval": interval, "days": days}
            )
            if response.ok:
                result = response.json()
                st.session_state.result = result

# 结果展示
if "result" in st.session_state:
    st.header("3️⃣ 回测结果")
    result = st.session_state.result
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总收益", f"{result['total_return']*100:.2f}%")
    col2.metric("最大回撤", f"{result['max_drawdown']*100:.2f}%")
    col3.metric("夏普比率", f"{result['sharpe_ratio']:.2f}")
    col4.metric("胜率", f"{result['win_rate']*100:.1f}%")
    
    # 收益曲线
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=result['equity_curve'], mode='lines', name='净值'))
    fig.update_layout(title="收益曲线", xaxis_title="时间", yaxis_title="净值")
    st.plotly_chart(fig, use_container_width=True)
```

---

## 4. 实施步骤

### Step 1: 项目初始化 ✅

```bash
# 创建项目结构
mkdir -p src/{api,ai,backtest,data,indicators,strategy}
mkdir -p frontend tests

# 创建 Conda 环境
conda create -n pyquantalpha python=3.13 -y
conda activate pyquantalpha

# 安装依赖
pip install fastapi uvicorn openai requests streamlit plotly pandas numpy python-dotenv pytest
```

### Step 2: 数据层 ✅

1. ✅ 实现 `BinanceClient` + 链式语法
2. ✅ 实现 `get_historical_klines()` 批量历史数据
3. ✅ 实现请求频率限制 (429/418 处理)
4. ✅ 完整单元测试 (55 个)

### Step 3: API 骨架 ✅

1. ✅ 创建 FastAPI 应用
2. ✅ 实现健康检查端点 `/health`
3. ✅ 实现占位端点 `/api/generate`, `/api/backtest`
4. ✅ 实现 K 线数据端点 `/api/klines` (调用 BinanceClient)
5. ✅ 启动服务，验证 Swagger 文档
6. ✅ 单元测试 (12 个)

### Step 4: AI 策略生成 ✅

1. ✅ 创建 `BaseLLMClient` 抽象基类
2. ✅ 封装 DeepSeek API
3. ✅ 预留 OpenAI 客户端
4. ✅ 实现工厂方法 + `LLMProvider` 枚举
5. ✅ 设计 Prompt 模板
6. ✅ 实现代码校验 (validator.py)
7. ✅ 更新 `/api/generate` 端点
8. ✅ 单元测试 (14 个)

### Step 5: 指标库 + 自定义指标支持（方案 B） ✅

> **设计决策**：采用「基础库 + 允许自定义」模式，既提供高效的内置指标，又允许 AI 生成任意自定义逻辑。

#### 5.1 基础指标库 (`src/indicators/`) ✅

创建一套高效、经过优化的基础指标供 AI 和回测引擎使用：

| 指标 | 类名 | 说明 |
|------|------|------|
| 简单移动平均 | `SMA(period)` | 基础趋势指标 |
| 指数移动平均 | `EMA(period)` | 平滑趋势指标 |
| 相对强弱指标 | `RSI(period)` | 超买超卖判断 |
| MACD | `MACD(fast, slow, signal)` | 趋势动量指标 |
| ATR | `ATR(period)` | 波动率指标 |
| 布林带 | `BollingerBands(period, std)` | 通道指标 |

**文件结构**：
```
src/indicators/
├── __init__.py      # 导出所有指标
├── base.py          # 指标基类
├── ma.py            # SMA, EMA
├── oscillator.py    # RSI, MACD
└── volatility.py    # ATR, BollingerBands
```

#### 5.2 动态白名单校验器 ✅

修改 `src/ai/validator.py`，支持识别代码中定义的类/函数名：

```python
def validate_strategy_code(code: str) -> Tuple[bool, str]:
    tree = ast.parse(code)
    
    # 1. 收集代码中定义的名称
    defined_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.FunctionDef):
            defined_names.add(node.name)
    
    # 2. 合并到允许列表
    allowed = ALLOWED_NAMES | ALLOWED_BUILTINS | defined_names
    
    # 3. 使用扩展后的白名单进行校验
    ...
```

#### 5.3 更新 Prompt 模板 ✅

在 `src/ai/prompt.py` 中明确告知 AI 可以自定义指标：

```markdown
## 可用指标（内置库）
- `EMA(period)`, `SMA(period)`, `RSI(period)`, `MACD(fast, slow, signal)`, `ATR(period)`

## 自定义指标
你可以定义自己的指标类，例如：

```python
class SuperTrend:
    def __init__(self, period, multiplier):
        self.atr = ATR(period)  # 可以使用内置指标
        self.multiplier = multiplier
        self.upper = None
        self.lower = None
    
    def update(self, bar):
        atr_value = self.atr.update(bar.high, bar.low, bar.close)
        # ... 计算逻辑
        return trend_direction
```

然后在 Strategy 中使用：
```python
class Strategy:
    def init(self):
        self.st = SuperTrend(10, 3)
```
```

#### 5.4 实施步骤 ✅

1. ✅ 创建 `src/indicators/base.py` - 指标基类
2. ✅ 实现 `SMA`, `EMA` (`src/indicators/ma.py`)
3. ✅ 实现 `RSI`, `MACD` (`src/indicators/oscillator.py`)
4. ✅ 实现 `ATR`, `BollingerBands` (`src/indicators/volatility.py`)
5. ✅ 修改 `validator.py` 支持动态白名单
6. ✅ 更新 `prompt.py` 添加自定义指标示例
7. ✅ 单元测试（指标计算准确性）


### **Step 6**: 回测引擎 (`docs/phase1/STEP6_BACKTEST_ENGINE.md`) ✅
1. ✅ 实现 Order, Position 数据结构 (`src/backtest/models.py`)
2. ✅ 实现 BacktestEngine 核心循环 (`src/backtest/engine.py`)
3. ✅ 实现绩效分析 (`src/backtest/analyzer.py`)
4. ✅ 单元测试 (`tests/test_backtest/` 219 passed)

### Step 7: 端点完善 ✅

1. ✅ **AI 交互升级**:
   - 修改 `src/ai/` 接口，支持返回 `(code, explanation)` 元组
   - 更新 `GenerateResponse` 增加 `explanation` 字段
   - 优化 Prompt 要求模型输出策略解读
2. ✅ **回测引擎集成**:
   - 修改 `BacktestEngine` 支持 `on_progress` 回调
   - 集成 `src/backtest` 到 API
3. ✅ **实时回测接口**:
   - 实现 `POST /api/backtest/run` 启动回测
   - 实现 `GET /api/backtest/stream` (SSE) 推送实时进度和净值更新

### Step 8: 前端 (Simple HTML)

1. [ ] **单页应用 (`index.html`)**:
   - 聊天输入框 (与 AI 交互)
   - 策略展示区 (代码高亮 + 策略解读)
   - 控制面板 (运行回测按钮)
   - 结果展示区 (实时进度条 + 净值曲线图)
2. [ ] **交互逻辑 (Vanilla JS)**:
   - `fetch` 调用生成接口
   - `EventSource` 监听回测进度
   - Chart.js 绘制简易图表

### Step 9: 集成测试

```bash
# 运行所有测试
pytest

# 运行指定模块
pytest tests/test_indicators/
```

测试文件结构：
```
tests/
├── test_data/test_binance.py      # 数据层测试
├── test_api/test_main.py          # API 测试
├── test_ai/test_validator.py      # 代码校验测试
├── test_indicators/test_ma.py     # 指标测试
└── test_backtest/test_engine.py   # 回测引擎测试
```

---

## 5. 依赖清单

```txt
# requirements.txt
fastapi>=0.124.0
uvicorn>=0.38.0
openai>=1.68.0
requests>=2.32.5
streamlit>=1.52.0
plotly>=6.5.0
pandas>=2.3.0
numpy>=2.3.0
python-dotenv>=1.2.0
pytest>=9.0.0
```

### Python 3.13 兼容性检查

| 依赖 | 版本 | Python 3.13 | 说明 |
|------|------|-------------|------|
| fastapi | 0.124.0 | ✅ 支持 | 官方支持 3.9-3.13 |
| uvicorn | 0.38.0 | ✅ 支持 | 官方支持 3.9-3.13 |
| openai | 1.68.0 | ✅ 支持 | 纯 Python 库 |
| requests | 2.32.5 | ✅ 支持 | 纯 Python 库 |
| streamlit | 1.52.0 | ✅ 支持 | 官方支持 3.9-3.13 |
| plotly | 6.5.0 | ✅ 支持 | 纯 Python 库 |
| pandas | 2.3.0 | ✅ 支持 | 2.2.3+ 支持 3.13 |
| numpy | 2.3.0 | ✅ 支持 | 2.1.0+ 支持 3.13 |
| python-dotenv | 1.2.0 | ✅ 支持 | 纯 Python 库 |
| pytest | 9.0.0 | ✅ 支持 | 官方支持 3.9-3.13 |

---

## 6. 环境变量

```bash
# .env
DEEPSEEK_API_KEY=your_api_key_here
```

---

*文档生成日期: 2025-12-10*
