# src/api/routes/health.py
"""健康检查端点"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """健康检查端点
    
    Returns:
        服务状态信息
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        "service": "PyQuantAlpha API"
    }
