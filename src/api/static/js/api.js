/**
 * API Client
 * 封装与后端服务的交互
 */

const API = {
    /**
     * 智能聊天（自动识别意图）
     * @param {string} message 用户消息
     * @returns {Promise<{type: string, content: string, explanation: string, is_valid: bool}>}
     */
    async chat(message) {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '请求失败');
        }

        return await res.json();
    },

    /**
     * 生成策略（直接生成，不判断意图）
     * @param {string} prompt 用户提示词
     * @returns {Promise<{code: string, explanation: string, is_valid: bool}>}
     */
    async generateStrategy(prompt) {
        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '生成失败');
        }

        return await res.json();
    },

    /**
     * 启动回测
     * @param {string} code 策略代码
     * @param {string} symbol 交易对
     * @param {string} interval 周期
     * @param {number} days 天数
     */
    async runBacktest(code, symbol, interval, days) {
        const res = await fetch('/api/backtest/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code,
                symbol,
                interval,
                days: parseInt(days)
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '回测启动失败');
        }

        return await res.json();
    },

    /**
     * 获取 SSE 流地址
     * @param {string} taskId 任务ID
     */
    getStreamUrl(taskId) {
        return `/api/backtest/stream/${taskId}`;
    }
};

