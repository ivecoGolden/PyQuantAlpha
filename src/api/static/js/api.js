/**
 * API Client
 * 封装与后端服务的交互
 */

const API = {
    /**
     * 统一上下文感知聊天
     * @param {string} message 用户消息
     * @param {string|null} contextCode 当前策略代码（可选）
     * @returns {Promise<{type: string, content: string, explanation: string, is_valid: bool}>}
     */
    async chat(message, contextCode = null) {
        const body = { message };
        if (contextCode) {
            body.context_code = contextCode;
        }

        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '请求失败');
        }

        return await res.json();
    },

    /**
     * 启动回测
     * @param {string} code 策略代码
     * @param {string} symbol 交易对
     * @param {string} interval 周期
     * @param {number} days 天数
     * @param {object} config 高级配置 {initial_capital, commission_rate, slippage}
     */
    async runBacktest(code, symbol, interval, days, config = {}) {
        const body = {
            code,
            symbol,
            interval,
            days: parseInt(days),
            // 高级配置（后端会验证并使用默认值）
            initial_capital: config.initial_capital || 100000,
            commission_rate: config.commission_rate || 0.001,
            slippage: config.slippage || 0.0005
        };

        const res = await fetch('/api/backtest/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
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
    },

    /**
     * 生成策略解读
     * @param {string} code 策略代码
     * @returns {Promise<{explanation: string}>}
     */
    async explainStrategy(code) {
        const res = await fetch('/api/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '解读生成失败');
        }

        return await res.json();
    }
};

