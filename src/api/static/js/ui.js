/**
 * UI Manager
 * 负责 DOM 操作和图表渲染
 */

const UI = {
    // Chart 实例
    chart: null,
    // 当前策略代码（用于复制）
    currentCode: "",

    // 初始化
    init() {
        this.initChart();
        this.bindTabs();
        this.bindCopyButton();
    },

    /**
     * 初始化图表
     */
    initChart() {
        const ctx = document.getElementById('equity-chart').getContext('2d');

        // 渐变背景
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.2)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0)');

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '账户净值 (Equity)',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: gradient,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false, // 实时更新关闭动画以提高性能
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(17, 24, 39, 0.9)',
                        titleColor: '#9ca3af',
                        bodyColor: '#f3f4f6',
                        borderColor: '#374151',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: '#6b7280', maxTicksLimit: 8 }
                    },
                    y: {
                        grid: { color: '#1f2937' },
                        ticks: { color: '#6b7280' }
                    }
                }
            }
        });
    },

    /**
     * 重置图表
     */
    resetChart() {
        if (!this.chart) return;
        this.chart.data.labels = [];
        this.chart.data.datasets[0].data = [];
        this.chart.update();
        document.getElementById('chart-overlay').classList.remove('hidden');
    },

    /**
     * 更新图表数据
     * @param {string} label 时间标签
     * @param {number} value 净值
     */
    updateChart(label, value) {
        if (!this.chart) return;

        document.getElementById('chart-overlay').classList.add('hidden');

        // 格式化时间 (显示日期和时间，以支持 intraday 数据)
        const dateObj = new Date(label);
        const dateStr = dateObj.toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });

        // 限制数据点数量，避免浏览器卡顿 (保留最近 1000 点或抽样)
        // 这里简化直接 push
        this.chart.data.labels.push(dateStr);
        this.chart.data.datasets[0].data.push(value);

        // 每 N 个点更新一次界面，或者由上层控制频率
        this.chart.update('none'); // 'none' mode ignores animation
    },

    /**
     * 添加聊天消息
     * @param {string} role 'user' | 'ai'
     * @param {string} text 消息内容
     * @param {string} id 可选消息 ID（用于后续更新）
     */
    addChatMessage(role, text, id = null) {
        const container = document.getElementById('chat-history');
        const isAI = role === 'ai';

        const msgId = id ? `id="msg-${id}"` : '';
        const html = `
            <div ${msgId} class="flex gap-3 ${!isAI ? 'flex-row-reverse' : ''} animate-fade-in">
                <div class="w-8 h-8 rounded-full ${isAI ? 'bg-blue-600' : 'bg-gray-600'} flex items-center justify-center flex-shrink-0">
                    <i data-lucide="${isAI ? 'bot' : 'user'}" class="w-5 h-5 text-white"></i>
                </div>
                <div class="msg-content ${isAI ? 'bg-gray-800' : 'bg-blue-600/20 border border-blue-500/30'} p-3 rounded-lg ${isAI ? 'rounded-tl-none' : 'rounded-tr-none'} max-w-[85%] text-sm leading-relaxed shadow-sm">
                    ${text}
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', html);
        container.scrollTop = container.scrollHeight;
        lucide.createIcons();
    },

    /**
     * 添加加载中消息（可更新）
     * @param {string} id 消息 ID
     * @param {string} text 加载中文本
     */
    addLoadingMessage(id, text = '⏳ 正在生成策略...') {
        this.addChatMessage('ai', `<span class="loading-text">${text}</span>`, id);
    },

    /**
     * 更新已有消息内容
     * @param {string} id 消息 ID
     * @param {string} newText 新内容
     */
    updateMessage(id, newText) {
        const msg = document.getElementById(`msg-${id}`);
        if (msg) {
            const content = msg.querySelector('.msg-content');
            if (content) {
                content.innerHTML = newText;
            }
        }
    },

    /**
     * 显示策略加载中状态
     */
    showStrategyLoading() {
        const codeEl = document.getElementById('code-display');
        codeEl.textContent = '# 策略生成中...';
        codeEl.classList.remove('hljs');

        // 隐藏复制按钮和已校验状态
        this.hideCopyButton();
        document.getElementById('strategy-status').classList.add('hidden');

        // 清空解读
        const expEl = document.getElementById('explanation-display');
        expEl.innerHTML = '<p class="text-gray-500 italic">等待生成...</p>';

        // 切换到代码 Tab
        this.switchTab('code');
    },

    /**
     * 更新策略显示
     * @param {string} code 
     * @param {string} explanation 
     */
    updateStrategyView(code, explanation) {
        this.currentCode = code;

        // 更新代码
        const codeEl = document.getElementById('code-display');

        // 重置 class 以确保 highlight.js 能重新识别 (移除 'hljs' 等 class，保留 'language-python')
        codeEl.className = 'language-python';
        codeEl.textContent = code;

        // 重新应用高亮
        hljs.highlightElement(codeEl);

        // 更新解读
        this.updateExplanation(explanation || '<i>正在生成策略解读...</i>');

        // 切换到代码 Tab
        this.switchTab('code');

        // 显示已校验状态和复制按钮
        document.getElementById('strategy-status').classList.remove('hidden');
        this.showCopyButton();
    },

    /**
     * 更新解读内容
     * @param {string} explanation 
     */
    updateExplanation(explanation) {
        const expEl = document.getElementById('explanation-display');
        expEl.innerHTML = marked.parse(explanation);
    },




    /**
     * 绑定复制按钮
     */
    bindCopyButton() {
        const btn = document.getElementById('copy-code-btn');
        if (btn) {
            btn.addEventListener('click', () => this.copyCode());
        }
    },

    /**
     * 显示复制按钮
     */
    showCopyButton() {
        const btn = document.getElementById('copy-code-btn');
        if (btn) btn.classList.remove('hidden');
    },

    /**
     * 隐藏复制按钮
     */
    hideCopyButton() {
        const btn = document.getElementById('copy-code-btn');
        if (btn) btn.classList.add('hidden');
    },

    /**
     * 复制代码到剪贴板
     */
    async copyCode() {
        if (!this.currentCode) return;

        try {
            await navigator.clipboard.writeText(this.currentCode);

            // 显示复制成功反馈
            const btn = document.getElementById('copy-code-btn');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i data-lucide="check" class="w-4 h-4"></i>';
            btn.classList.add('text-green-400');
            lucide.createIcons();

            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('text-green-400');
                lucide.createIcons();
            }, 2000);
        } catch (err) {
            console.error('复制失败:', err);
        }
    },

    /**
     * 绑定 Tab 切换逻辑
     */
    bindTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target.dataset.tab;
                this.switchTab(target);
            });
        });
    },

    /**
     * 切换 Tab
     */
    switchTab(tabName) {
        // Update Buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            const isTarget = btn.dataset.tab === tabName;
            if (isTarget) {
                btn.classList.add('text-blue-400', 'border-blue-400');
                btn.classList.remove('text-gray-400', 'border-transparent');
            } else {
                btn.classList.remove('text-blue-400', 'border-blue-400');
                btn.classList.add('text-gray-400', 'border-transparent');
            }
        });

        // Update Content
        document.querySelectorAll('.tab-content').forEach(el => {
            el.classList.add('hidden');
        });
        document.getElementById(`view-${tabName}`).classList.remove('hidden');
    },

    /**
     * 更新进度条
     */
    updateProgress(percent) {
        const bar = document.getElementById('progress-bar');
        const text = document.getElementById('progress-text');
        bar.style.width = `${percent}%`;
        text.textContent = `${percent}%`;
    },

    /**
     * 更新指标卡片
     */
    updateMetrics(data) {
        if (!data) return;

        const formatPercent = (v) => {
            if (v === null || v === undefined || isNaN(v)) return '--%';
            return (v * 100).toFixed(2) + '%';
        };
        const formatNum = (v) => {
            if (v === null || v === undefined || isNaN(v)) return '--';
            return v.toFixed(2);
        };

        document.getElementById('metric-return').textContent = formatPercent(data.total_return);
        document.getElementById('metric-drawdown').textContent = formatPercent(data.max_drawdown);
        document.getElementById('metric-sharpe').textContent = formatNum(data.sharpe_ratio);
        // 如果后端返回 0 但实际上是一次交易都没做，也可以考虑显示 --，但这里遵循数据
        document.getElementById('metric-winrate').textContent = formatPercent(data.win_rate);

        // 更新图表标题中的交易对
        if (data.symbols && data.symbols.length > 0) {
            this.setChartSymbol(data.symbols[0]);
        }
    },

    /**
     * 设置图表标题中的交易对
     * @param {string} symbol 交易对名称
     */
    setChartSymbol(symbol) {
        const el = document.getElementById('chart-symbol');
        if (el) {
            el.textContent = symbol || 'BTCUSDT';
        }
    }
};

// 简单的淡入动画
const style = document.createElement('style');
style.innerHTML = `
    .animate-fade-in { animation: fadeIn 0.3s ease-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
`;
document.head.appendChild(style);

