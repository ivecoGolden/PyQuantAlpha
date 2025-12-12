# Step 8: 前端开发 (Frontend Development) 实施详情

> **目标**: 构建一个轻量级、响应式的 Web 界面，实现与 AI 的自然语言交互、策略代码可视化以及实时回测展示。

---

## 1. 技术栈选择

为了保持项目简洁并快速迭代，我们采用 **"No-Build"** 方案，直接使用原生技术标准：

-   **HTML5 / CSS3**: 语义化标签，Flexbox/Grid 布局。
-   **TailwindCSS (CDN)**: 快速样式开发，保证现代化的视觉效果 (`v3.x`)。
-   **Vanilla JavaScript (ES6+)**: 无需构建工具（Webpack/Vite），直接在浏览器运行。
-   **三方库 (CDN)**:
    -   `marked.js`: Markdown 渲染（用于显示策略解读）。
    -   `highlight.js`: 代码高亮。
    -   `Chart.js`: 绘制回测净值曲线。
    -   `lucide`: 图标库。

---

## 2. 页面布局设计

采用 **"双栏 IDE 风格"** 布局：

### 2.1 左侧栏 (交互区) - 30% 宽度
1.  **聊天窗口 (Chat Interface)**:
    -   消息历史列表（用户提问、AI 回复）。
    -   输入框 + 发送按钮。
    -   AI 回复包含简短文本和 "策略已生成" 提示。

### 2.2 右侧栏 (工作区) - 70% 宽度
1.  **上部：策略展示 (Strategy Viewer)**
    -   **Tabs**: `代码 (Code)` / `解读 (Explanation)`。
    -   **代码视图**: 只读编辑器样式，带语法高亮。
    -   **解读视图**: Markdown 渲染的策略逻辑说明。
    
2.  **Toolbar (操作栏)**
    -   回测参数配置：`Symbol` (BTCUSDT), `Interval` (1h), `Days` (30).
    -   **"运行回测" 按钮**: 触发回测流程。
    -   **进度条**: 显示 SSE 实时进度。

3.  **下部：回测结果 (Results Dashboard)**
    -   **核心指标卡片**: 总收益率, 最大回撤, 夏普比率, 胜率, 交易次数。
    -   **净值曲线图**: 实时更新的折线图。

---

## 3. 功能流程详解

### 3.1 策略生成流程
1.  用户在左侧输入："帮我写一个双均线策略，20和60日线"。
2.  JS 调用 `POST /api/generate`。
3.  Loading 状态：输入框禁用，显示 "AI 思考中..."。
4.  响应返回：
    -   将 `explanation` 渲染到解读标签页。
    -   将 `code` 渲染到代码标签页。
    -   自动切换到右侧工作区。

### 3.2 实时回测流程
1.  用户点击 "运行回测"。
2.  JS 获取当前显示的 `code` 和配置参数。
3.  调用 `POST /api/backtest/run` 启动任务，获取 `task_id`。
4.  JS 创建 `EventSource` 连接 `/api/backtest/stream/{task_id}`。
5.  **监听事件**:
    -   `progress`: 更新进度条宽度，向 Chart.js 添加新的数据点（需控制重绘频率）。
    -   `result`: 回测结束，更新指标卡片数字，断开 SSE 连接。
    -   `error`: 显示错误 Toast，断开连接。

---

## 4. 文件结构

前段代码将直接放在 `src/api/static/` 目录下，由 FastAPI 挂载静态文件服务。

```
src/api/
├── static/
│   ├── index.html      # 主页面结构
│   ├── css/
│   │   └── style.css   # 自定义样式微调
│   └── js/
│       ├── app.js      # 主应用逻辑
│       ├── api.js      # API 封装
│       └── ui.js       # UI 渲染与更新
└── main.py             # 需修改以挂载 StaticFiles
```

---

## 5. 实施任务分解

1.  **环境准备**:
    -   配置 FastAPI `StaticFiles`。
    -   创建基础 HTML 骨架。

2.  **UI 开发**:
    -   引入 TailwindCSS。
    -   搭建左右分栏布局。
    -   实现 Chat 组件和 Tabs 组件。

3.  **逻辑对接 - 生成**:
    -   实现 `generateStrategy` 函数。
    -   Markdown 和代码高亮渲染。

4.  **逻辑对接 - 回测**:
    -   实现 `runBacktest` 和 `connectSSE`。
    -   集成 Chart.js 实现动态图表更新。
    -   实现指标自动计算与展示。

5.  **调试与优化**:
    -   Mobile 适配调整（可选）。
    -   错误处理 UI。
