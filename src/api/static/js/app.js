/**
 * Main Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    UI.init();

    // Globals
    let currentCode = "";

    // Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const runBtn = document.getElementById('run-backtest-btn');

    // ============ Chat & Generate ============

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
            // 使用新的 chat API（自动识别意图）
            const res = await API.chat(message);

            if (res.type === 'strategy') {
                // 策略生成模式
                UI.updateMessage(msgId, '⏳ 正在生成策略...');
                UI.showStrategyLoading();

                // 短暂延迟后更新消息（模拟加载效果）
                await new Promise(r => setTimeout(r, 300));

                if (res.is_valid) {
                    UI.updateMessage(msgId, `✅ 策略生成成功！<br>已在右侧加载代码和解读。`);
                } else {
                    UI.updateMessage(msgId, `⚠️ ${res.message}<br>代码已加载，但可能存在问题。`);
                }

                currentCode = res.content;
                UI.updateStrategyView(res.content, res.explanation || "无解读");
            } else {
                // 普通聊天模式 - 替换加载消息为回复
                UI.updateMessage(msgId, res.content);
            }

        } catch (err) {
            // 更新加载消息为错误
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

        // Params
        const symbol = document.getElementById('bt-symbol').value;
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
