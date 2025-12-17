/**
 * Main Application Logic
 */

// Phase 2.1: Logs/Trades Tab Switching
function switchLogTab(tab) {
    const logsPanel = document.getElementById('panel-logs');
    const tradesPanel = document.getElementById('panel-trades');
    const logsBtn = document.getElementById('tab-logs-btn');
    const tradesBtn = document.getElementById('tab-trades-btn');

    if (tab === 'logs') {
        logsPanel.classList.remove('hidden');
        tradesPanel.classList.add('hidden');
        logsBtn.classList.replace('bg-gray-700', 'bg-blue-600');
        logsBtn.classList.replace('text-gray-400', 'text-white');
        tradesBtn.classList.replace('bg-blue-600', 'bg-gray-700');
        tradesBtn.classList.replace('text-white', 'text-gray-400');
    } else {
        logsPanel.classList.add('hidden');
        tradesPanel.classList.remove('hidden');
        tradesBtn.classList.replace('bg-gray-700', 'bg-blue-600');
        tradesBtn.classList.replace('text-gray-400', 'text-white');
        logsBtn.classList.replace('bg-blue-600', 'bg-gray-700');
        logsBtn.classList.replace('text-white', 'text-gray-400');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    UI.init();

    // Globals
    let currentCode = "";
    let currentSymbol = "BTCUSDT";

    // Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const runBtn = document.getElementById('run-backtest-btn');

    // ============ Chat ============

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        // UI State: Loading
        UI.addChatMessage('user', message);
        userInput.value = '';
        userInput.disabled = true;
        sendBtn.disabled = true;

        // 生成唯一消息 ID，显示加载状态
        const msgId = Date.now().toString();
        UI.addLoadingMessage(msgId, '💭 正在想...');

        try {
            // 统一 API 调用，带上当前代码上下文
            const res = await API.chat(message, currentCode || null);

            if (res.type === 'strategy') {
                // 策略生成/修改模式
                if (res.is_valid) {
                    UI.updateMessage(msgId, `✅ 策略已生成！`);
                } else {
                    UI.updateMessage(msgId, `⚠️ ${res.message}<br>代码已加载，但可能存在问题。`);
                }

                currentCode = res.content;
                // 先显示代码，解读暂为空
                UI.updateStrategyView(res.content, "");

                // 更新交易对显示（从策略中提取）
                if (res.symbols && res.symbols.length > 0) {
                    currentSymbol = res.symbols[0];
                    document.getElementById('bt-symbol').textContent = currentSymbol;
                    document.getElementById('chart-symbol').textContent = currentSymbol;
                }

                // 异步获取解读
                API.explainStrategy(res.content).then(expRes => {
                    UI.updateExplanation(expRes.explanation);
                }).catch(err => {
                    console.error("解读生成失败", err);
                    UI.updateExplanation("⚠️ 自动解读生成失败，请稍后重试。");
                });

            } else {
                // 普通聊天模式
                UI.updateMessage(msgId, res.content);
            }

        } catch (err) {
            UI.updateMessage(msgId, `❌ 发生错误: ${err.message}`);
        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });

    // Enter to submit
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // ============ Backtest ============

    let eventSource = null;

    runBtn.addEventListener('click', async () => {
        if (!currentCode) {
            alert("请先生成或输入策略代码");
            return;
        }

        // Params - symbol 从 span 读取
        const symbol = document.getElementById('bt-symbol').textContent;
        const interval = document.getElementById('bt-interval').value;
        const days = document.getElementById('bt-days').value;

        try {
            // UI Reset
            runBtn.disabled = true;
            runBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> 回测中...`;
            lucide.createIcons();
            UI.resetChart();
            UI.updateProgress(0);

            // 1. Start Task
            const { task_id } = await API.runBacktest(currentCode, symbol, interval, days);

            // 2. Connect SSE
            if (eventSource) eventSource.close();
            eventSource = new EventSource(API.getStreamUrl(task_id));

            eventSource.onopen = () => {
                console.log("SSE Connected");
            };

            eventSource.onmessage = (e) => {
                // 默认 data 应该 parsed? 
                // SSE 格式通常 data: {...}
                // EventSource 自动处理了格式，但 e.data 是字符串
                try {
                    const payload = JSON.parse(e.data);
                    // 理论上我们在 manager 里还没区分 event type 到 onmessage，
                    // 而是用了 event: type. 所以应该监听具体事件
                } catch (err) {
                    console.error("Parse error", err);
                }
            };

            // 监听自定义事件 types
            eventSource.addEventListener('progress', (e) => {
                const data = JSON.parse(e.data);
                // 更新进度条
                UI.updateProgress(data.progress);
                // 更新图表 - equity 是浮点数，timestamp 是单独的字段
                UI.updateChart(data.timestamp || Date.now(), data.equity);
            });

            eventSource.addEventListener('result', (e) => {
                const data = JSON.parse(e.data); // BacktestResult
                UI.updateProgress(100);
                UI.updateMetrics(data); // { total_return, ... }

                // Phase 2.1: 渲染可视化数据
                if (data.visuals) {
                    UI.renderLogs(data.visuals.logs);
                    UI.renderTrades(data.visuals.trades);
                }

                // 完整重绘图表以确保精确（如果之前是抽样）
                // 这里暂略，直接使用流式数据

                stopBacktest(false);
            });

            eventSource.addEventListener('error', (e) => {
                const data = JSON.parse(e.data);
                alert(`回测错误: ${data.message}`);
                stopBacktest(true);
            });

            eventSource.onerror = (err) => {
                console.error("SSE Error", err);
                // 可能是连接断开
                if (eventSource.readyState === EventSource.CLOSED) {
                    stopBacktest(false);
                } else {
                    // stopBacktest(true); // 暂时不强制停止，有时是网络波动
                }
            };

        } catch (err) {
            alert(err.message);
            stopBacktest(true);
        }
    });

    function stopBacktest(isError) {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        runBtn.disabled = false;
        runBtn.innerHTML = `<i data-lucide="play" class="w-4 h-4"></i> 运行回测`;
        lucide.createIcons();
    }
});
