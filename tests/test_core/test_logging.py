# tests/test_core/test_logging.py
"""日志配置测试"""

import pytest
import logging
from unittest.mock import patch, MagicMock

from src.core.logging import setup_logging, logger


class TestSetupLogging:
    """setup_logging 函数测试"""
    
    def test_setup_logging_creates_handler(self):
        """测试 setup_logging 创建 handler"""
        setup_logging()
        
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
    
    def test_setup_logging_sets_level(self):
        """测试 setup_logging 设置日志级别"""
        setup_logging()
        
        root_logger = logging.getLogger()
        # 默认是 INFO
        assert root_logger.level <= logging.INFO
    
    @patch('src.core.logging.settings')
    def test_setup_logging_debug_level(self, mock_settings):
        """测试 DEBUG 日志级别"""
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_JSON_FORMAT = False
        
        setup_logging()
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    @patch('src.core.logging.settings')
    def test_setup_logging_json_format(self, mock_settings):
        """测试 JSON 格式日志"""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_JSON_FORMAT = True
        
        setup_logging()
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[0]
        # JSON 格式包含 "timestamp"
        assert "timestamp" in handler.formatter._fmt
    
    @patch('src.core.logging.settings')
    def test_setup_logging_standard_format(self, mock_settings):
        """测试标准格式日志"""
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_JSON_FORMAT = False
        
        setup_logging()
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[0]
        # 标准格式包含 levelname
        assert "levelname" in handler.formatter._fmt


class TestLogger:
    """logger 实例测试"""
    
    def test_logger_exists(self):
        """测试 logger 实例存在"""
        assert logger is not None
    
    def test_logger_name(self):
        """测试 logger 名称"""
        assert logger.name == "pyquantalpha"
    
    def test_logger_is_logging_logger(self):
        """测试 logger 是 logging.Logger 实例"""
        assert isinstance(logger, logging.Logger)
