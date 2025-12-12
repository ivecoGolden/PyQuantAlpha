# Bug 修复记录

本文档记录项目中发现并修复的 Bug。

---

## 2024-12-12

### Bug #001: 前端图表数据解析错误

**文件**: `src/api/static/js/app.js`

**问题描述**:  
SSE 进度事件中，代码错误地使用 `data.equity.timestamp` 访问时间戳，但 `equity` 实际上是浮点数而非对象。

**错误代码**:
```javascript
UI.updateChart(data.equity.timestamp || Date.now(), data.equity);
```

**修复后**:
```javascript
UI.updateChart(data.timestamp || Date.now(), data.equity);
```

**影响**: 图表无法正确渲染实时净值曲线。

---

### Bug #002: 回测结果缺少关键统计字段

**文件**: `src/backtest/manager.py`

**问题描述**:  
SSE 返回的 `result` 事件中缺少 `win_rate`、`profit_factor`、`total_trades` 字段，导致前端无法显示这些指标。

**修复**: 在结果 payload 中添加缺失字段：
```python
"win_rate": result.win_rate,
"profit_factor": result.profit_factor,
"total_trades": result.total_trades,
```

**影响**: 前端胜率等指标显示为 `--`。

---

### Bug #003: 持仓检测逻辑错误 ⚠️ 关键

**文件**: `src/backtest/engine.py`

**问题描述**:  
`_api_get_position()` 方法在持仓平仓后（quantity=0）仍返回 `Position` 对象而非 `None`，导致策略中 `if get_position(symbol) is None` 的判断失效，无法重新开仓。

**错误代码**:
```python
def _api_get_position(self, symbol: str) -> Optional[Position]:
    return self.positions.get(symbol)
```

**修复后**:
```python
def _api_get_position(self, symbol: str) -> Optional[Position]:
    position = self.positions.get(symbol)
    if position is None or position.quantity == 0:
        return None
    return position
```

**影响**: 策略只能执行一次买入-卖出周期，之后无法再开仓。

---

## 模板

```markdown
### Bug #XXX: 简短描述

**文件**: `path/to/file`

**问题描述**:  
详细描述问题的原因和表现。

**错误代码**:
（可选）

**修复后**:
描述修复方案或代码。

**影响**: 该 bug 造成的影响。
```
