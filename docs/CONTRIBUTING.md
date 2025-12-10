# 开发规范

## 1. 代码风格

### Python

- 遵循 **PEP 8** 规范
- 使用 **类型注解**
- 函数/类需要 **docstring**

```python
def get_klines(symbol: str, interval: str, limit: int = 100) -> List[Bar]:
    """获取 K 线数据
    
    Args:
        symbol: 交易对，如 "BTCUSDT"
        interval: 时间周期，如 "1h"
        limit: 返回数量
        
    Returns:
        K 线数据列表
    """
```

## 2. 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | 小写+下划线 | `binance_client.py` |
| 类名 | PascalCase | `BinanceClient` |
| 函数/变量 | snake_case | `get_klines` |
| 常量 | 大写+下划线 | `BASE_URL` |

## 3. 项目结构

```
src/模块名/
├── __init__.py    # 导出公共接口
├── 主文件.py      # 核心实现
└── models.py      # 数据模型
```

## 4. Git 提交规范

```
<type>: <description>

feat: 新功能
fix: 修复 bug
docs: 文档更新
refactor: 重构
test: 测试
```

示例：
```
feat: 实现 BinanceClient.get_klines
fix: 修复 EMA 计算精度问题
docs: 更新 README
```

## 5. 测试规范

- 测试文件：`tests/test_<模块>/test_<文件>.py`
- 测试函数：`test_<功能描述>`
- 使用 **pytest**

```bash
# 运行测试
pytest
pytest tests/test_data/ -v
```

## 6. 文档规范

- 每个阶段创建独立文档目录
- 重要模块需要详细说明文档
- 文档使用 Markdown 格式

```
docs/
├── ARCHITECTURE.md      # 总体架构
├── CONTRIBUTING.md      # 开发规范（本文档）
└── phase1/              # 阶段文档
```

## 7. 环境变量

敏感信息使用 `.env` 文件：

```bash
# .env
DEEPSEEK_API_KEY=your_key_here
```

**注意**：`.env` 不要提交到 Git

## 8. 错误消息规范

### 格式

```python
raise ErrorType("模块名: 简短描述。详情: {具体值}")
```

### 错误类型

| 场景 | 错误类型 | 示例 |
|------|---------|------|
| 参数无效 | `ValueError` | 无效的交易对 |
| 类型错误 | `TypeError` | 期望 str，收到 int |
| 连接失败 | `ConnectionError` | API 请求超时 |
| 数据异常 | `RuntimeError` | 返回数据为空 |

### 示例

```python
# ✓ 正确
raise ValueError(f"BinanceClient: 无效的交易对。symbol={symbol}")
raise ConnectionError(f"BinanceClient: API 请求失败。status={response.status_code}")

# ✗ 错误
raise ValueError("error")  # 太模糊
raise Exception("无效")    # 类型不具体
```

### 日志记录

```python
import logging

logger = logging.getLogger(__name__)

# 错误级别
logger.error(f"请求失败: {e}")
logger.warning(f"重试第 {retry} 次")
logger.info(f"获取 {len(bars)} 条数据")
logger.debug(f"请求参数: {params}")
```

---

*最后更新: 2025-12-10*
