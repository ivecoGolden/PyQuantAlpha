# src/database/database.py
"""
数据库连接管理

- 使用 SQLAlchemy 2.0 异步引擎
- 默认开启 WAL 模式支持并发读写
- 提供依赖注入函数
"""

from __future__ import annotations

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, text


# 数据库文件路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATABASE_PATH = DATA_DIR / "market_data.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"


class Base(DeclarativeBase):
    """ORM 模型基类"""
    pass


# 全局引擎实例（惰性初始化）
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _enable_wal(dbapi_conn, connection_record) -> None:
    """启用 WAL 模式的回调函数"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")
    cursor.close()


def get_engine() -> AsyncEngine:
    """获取数据库引擎（单例）
    
    Returns:
        异步数据库引擎
    """
    global _engine
    
    if _engine is None:
        # 确保数据目录存在
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,  # 生产环境关闭 SQL 日志
            pool_pre_ping=True,
        )
        
        # 监听连接事件，启用 WAL 模式
        event.listen(_engine.sync_engine, "connect", _enable_wal)
    
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取会话工厂（单例）
    
    Returns:
        异步会话工厂
    """
    global _session_factory
    
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（上下文管理器）
    
    用于依赖注入或手动管理会话生命周期。
    
    Yields:
        异步数据库会话
        
    Example:
        >>> async with get_session() as session:
        ...     result = await session.execute(select(Candlestick))
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """初始化数据库（创建所有表）
    
    在应用启动时调用，确保表结构存在。
    """
    from .models import Candlestick  # 避免循环导入
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接
    
    在应用关闭时调用，释放资源。
    """
    global _engine, _session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
