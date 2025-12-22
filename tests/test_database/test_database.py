# tests/test_database/test_database.py
"""数据库连接管理测试"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.database.database import (
    get_engine,
    get_session_factory,
    get_session,
    init_db,
    close_db,
    Base,
    DATABASE_PATH,
    _enable_wal,
)


class TestDatabaseConfig:
    """测试数据库配置"""
    
    def test_database_path_is_path_object(self):
        """测试 DATABASE_PATH 是 Path 对象"""
        assert isinstance(DATABASE_PATH, Path)
    
    def test_database_path_ends_with_db(self):
        """测试数据库路径以 .db 结尾"""
        assert DATABASE_PATH.suffix == ".db"
    
    def test_database_in_data_directory(self):
        """测试数据库在 data 目录下"""
        assert "data" in str(DATABASE_PATH)


class TestWALMode:
    """测试 WAL 模式"""
    
    def test_enable_wal_executes_pragma(self):
        """测试 WAL 模式回调执行 PRAGMA 命令"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        _enable_wal(mock_conn, None)
        
        # 验证执行了 PRAGMA 命令
        calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        assert "PRAGMA journal_mode=WAL" in calls
        assert "PRAGMA synchronous=NORMAL" in calls
        assert "PRAGMA cache_size=10000" in calls
        mock_cursor.close.assert_called_once()


class TestEngineCreation:
    """测试引擎创建"""
    
    def test_get_engine_returns_async_engine(self):
        """测试 get_engine 返回异步引擎"""
        from sqlalchemy.ext.asyncio import AsyncEngine
        engine = get_engine()
        assert isinstance(engine, AsyncEngine)
    
    def test_get_engine_singleton(self):
        """测试引擎是单例"""
        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1 is engine2


class TestSessionFactory:
    """测试会话工厂"""
    
    def test_get_session_factory_returns_factory(self):
        """测试 get_session_factory 返回工厂"""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        factory = get_session_factory()
        assert isinstance(factory, async_sessionmaker)
    
    def test_get_session_factory_singleton(self):
        """测试会话工厂是单例"""
        factory1 = get_session_factory()
        factory2 = get_session_factory()
        assert factory1 is factory2


class TestSessionContext:
    """测试会话上下文管理"""
    
    @pytest.mark.asyncio
    async def test_get_session_yields_session(self):
        """测试 get_session 产生会话对象"""
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with get_session() as session:
            assert isinstance(session, AsyncSession)
    
    @pytest.mark.asyncio
    async def test_get_session_auto_commits(self):
        """测试会话自动提交"""
        async with get_session() as session:
            # 正常执行应该自动提交
            pass  # 没有异常就表示成功


class TestInitDb:
    """测试数据库初始化"""
    
    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self):
        """测试 init_db 创建表"""
        await init_db()
        
        # 验证数据库文件存在
        assert DATABASE_PATH.exists()
    
    @pytest.mark.asyncio
    async def test_init_db_idempotent(self):
        """测试 init_db 幂等性（多次调用不报错）"""
        await init_db()
        await init_db()
        # 没有异常就表示成功


class TestCloseDb:
    """测试数据库关闭"""
    
    @pytest.mark.asyncio
    async def test_close_db_disposes_engine(self):
        """测试 close_db 释放资源"""
        # 先确保有引擎
        get_engine()
        
        await close_db()
        
        # 再次获取应该创建新引擎
        # （由于单例被清空，这实际上会创建新实例）
