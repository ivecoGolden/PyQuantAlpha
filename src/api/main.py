# src/api/main.py
"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.api.routes import health, klines, strategy
from src.core.logging import setup_logging, logger
from src.config.settings import settings

# 加载环境变量
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    setup_logging()
    logger.info("🚀 PyQuantAlpha API 启动成功")
    logger.info(f"📖 文档地址: http://localhost:8000/docs")
    yield
    logger.info("👋 PyQuantAlpha API 已关闭")


app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应设置为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from pathlib import Path
from fastapi.staticfiles import StaticFiles

# ... existing imports ...

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(klines.router, prefix="/api", tags=["数据"])
app.include_router(strategy.router, prefix="/api", tags=["策略"])

from fastapi.responses import FileResponse

# 挂载静态文件
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse(static_dir / "index.html")
