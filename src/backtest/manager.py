# src/backtest/manager.py
"""
回测任务管理器

异步回测任务管理，支持 SSE 实时进度推送：
- 任务队列管理 (asyncio.Queue)
- 线程安全的进度回调
- SSE 事件流生成
- 绩效数据 + 可视化数据打包返回
"""
import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from src.data.models import Bar
from src.backtest.engine import BacktestEngine, BacktestResult

logger = logging.getLogger(__name__)


class BacktestManager:
    """全局回测管理器 (单例模式)
    
    负责:
    1. 管理运行中的回测任务
    2. 提供事件流队列 (SSE)
    3. 异步执行回测
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.tasks = {}  # task_id -> {"queue": Queue, "status": str}
        return cls._instance
    
    async def start_backtest(
        self,
        strategy_code: str,
        data: List[Bar],
        config: dict = None
    ) -> str:
        """启动异步回测任务
        
        Args:
            strategy_code: 策略代码
            data: K 线数据
            config: 回测配置
            
        Returns:
            task_id
        """
        task_id = str(uuid.uuid4())
        queue = asyncio.Queue()
        
        self.tasks[task_id] = {
            "queue": queue,
            "status": "running",
            "created_at": datetime.now()
        }
        
        # 启动后台任务
        asyncio.create_task(self._run_task(task_id, strategy_code, data, config))
        
        logger.info(f"回测任务启动: {task_id}")
        return task_id
    
    async def stream_events(self, task_id: str):
        """生成 SSE 事件流"""
        task = self.tasks.get(task_id)
        if not task:
            yield self._format_sse("error", {"message": "任务不存在"})
            return
            
        queue = task["queue"]
        
        try:
            while True:
                event = await queue.get()
                yield self._format_sse(event["type"], event["data"])
                
                # 如果是 finish 或 error，结束流
                if event["type"] in ("result", "error"):
                    break
        finally:
            # 清理任务
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    async def _run_task(self, task_id: str, code: str, data: list[Bar], config: dict):
        """执行回测逻辑"""
        queue = self.tasks[task_id]["queue"]
        
        def on_progress(current, total, equity):
            # 放入队列 (非阻塞)
            try:
                queue.put_nowait({
                    "type": "progress",
                    "data": {
                        "progress": int(current / total * 100),
                        "current": current,
                        "total": total,
                        "equity": equity
                    }
                })
            except asyncio.QueueFull:
                pass
            
            # 适当让出控制权，避免阻塞事件循环
            # await asyncio.sleep(0) # 无法在同步回调中使用 await
        
        try:
            # 在线程池中运行同步的回测引擎，避免阻塞主循环
            # 但 on_progress 需要与 asyncio 交互，这比较复杂
            # 这里简化处理：直接调用(因为是计算密集型，最好用 run_in_executor)
            # 为了简单演示 SSE，先直接运行
            
            # 兼容性处理：BacktestEngine 是同步的
            # 如果数据量大，应该使用 loop.run_in_executor
            
            from src.backtest.models import BacktestConfig
            bt_config = BacktestConfig(**(config or {})) if config else BacktestConfig()
            engine = BacktestEngine(config=bt_config)
            
            # 包装 on_progress 以适应 asyncio
            # 由于 run_in_executor 不支持回调中的异步，改为定期检查或直接放入 queue (queue 是线程安全的吗? asyncio.Queue 不是线程安全的)
            # 修正：asyncio.Queue 不是线程安全的。如果用 run_in_executor，需要 loop.call_soon_threadsafe
            
            loop = asyncio.get_running_loop()
            
            def thread_safe_progress(c, t, e, ts):
                # 降低日志频率，每 10% 或最后一次记录
                if t > 0 and (c % (t // 10 + 1) == 0 or c == t):
                    logger.info(f"Progress: {c}/{t}")
                
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "progress",
                        "data": {
                            "progress": int(c/t*100), 
                            "equity": e,
                            "timestamp": ts
                        }
                    }
                )
            
            logger.info(f"Starting engine.run in executor for task {task_id}")
            # 在线程池运行
            result = await loop.run_in_executor(
                None, 
                engine.run, 
                code, 
                data, 
                thread_safe_progress
            )
            
            # 发送结果
            await queue.put({
                "type": "result",
                "data": {
                    "total_return": result.total_return,
                    "max_drawdown": result.max_drawdown,
                    "sharpe_ratio": result.sharpe_ratio,
                    "win_rate": result.win_rate,
                    "profit_factor": result.profit_factor,
                    "total_trades": result.total_trades,
                    "equity_curve": result.equity_curve, 
                    "trades": [
                        {
                            "symbol": t.symbol,
                            "side": t.side.value,
                            "price": t.price,
                            "quantity": t.quantity,
                            "pnl": t.pnl,
                            "timestamp": t.timestamp
                        } for t in result.trades
                    ],
                    # Phase 2.1: 可视化数据（从 result.logs 中获取）
                    "logs": [
                        {
                            "timestamp": entry.timestamp,
                            "orders": entry.orders,
                            "positions": entry.positions,
                            "equity": entry.equity
                        } for entry in result.logs
                    ]
                }
            })
            
        except Exception as e:
            logger.error(f"回测任务异常: {e}")
            await queue.put({
                "type": "error",
                "data": {"message": str(e)}
            })
    
    def _format_sse(self, event_type: str, data: dict) -> str:
        """格式化 SSE 消息"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
