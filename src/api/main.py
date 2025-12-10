# src/api/main.py
"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from src.api.routes import health, klines, strategy

# 加载环境变量
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 PyQuantAlpha API 启动成功")
    print("📖 文档地址: http://localhost:8000/docs")
    yield
    print("👋 PyQuantAlpha API 已关闭")


app = FastAPI(
    title="PyQuantAlpha API",
    description="AI 量化策略平台 API - 支持策略生成与回测",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(klines.router, prefix="/api", tags=["数据"])
app.include_router(strategy.router, prefix="/api", tags=["策略"])
