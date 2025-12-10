# PyQuantAlpha

> AI 驱动的量化交易策略生成与执行平台

## 项目概述

PyQuantAlpha 是一个基于 AI 的量化交易平台，支持：

- 🧠 **自然语言策略生成** - 用自然语言描述交易策略，AI 自动生成代码
- 📊 **回测引擎** - 自研回测系统，支持 Binance 历史数据
- 🖥️ **可视化界面** - Streamlit 前端展示回测结果

## 技术栈

| 模块 | 技术 |
|------|------|
| AI 模型 | DeepSeek |
| 数据源 | Binance API |
| 后端 | FastAPI |
| 前端 | Streamlit |
| 回测 | 自研引擎 |

## 快速开始

```bash
# 创建环境
conda create -n pyquantalpha python=3.13 -y
conda activate pyquantalpha

# 安装依赖
pip install -r requirements-dev.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
```

## 项目结构

```
PyQuantAlpha/
├── docs/                    # 项目文档
│   ├── ARCHITECTURE.md      # 系统架构
│   ├── FEASIBILITY_REPORT.md
│   └── phase1/              # 第一阶段开发文档
├── src/                     # 源代码
│   ├── api/                 # API 服务
│   ├── ai/                  # AI 策略生成
│   ├── backtest/            # 回测引擎
│   ├── data/                # 数据层
│   └── indicators/          # 技术指标
├── frontend/                # 前端
├── tests/                   # 测试
└── requirements.txt
```

## 文档

- [系统架构](docs/ARCHITECTURE.md)
- [可行性报告](docs/FEASIBILITY_REPORT.md)
- [开发规范](docs/CONTRIBUTING.md)
- [Phase 1 实施计划](docs/phase1/IMPLEMENTATION_PLAN.md)

## 开发进度

- [x] 项目规划
- [x] 环境配置
- [ ] 数据层开发
- [ ] 指标库开发
- [ ] 回测引擎开发
- [ ] AI 策略生成
- [ ] API 服务
- [ ] 前端开发

## License

MIT
