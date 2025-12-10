import sys
import logging
from src.config.settings import settings

def setup_logging():
    """配置日志系统"""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # 清除现有的 handlers
    root_logger.handlers = []
    
    # 创建控制台 handler
    handler = logging.StreamHandler(sys.stdout)
    
    # 设置格式
    if settings.LOG_JSON_FORMAT:
        # 简单模拟 JSON 格式，实际生产建议使用 python-json-logger 或 structlog
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # 调整第三方库的日志级别
    logging.getLogger("uvicorn.access").handlers = []  # 避免 uvicorn 重复处理
    logging.getLogger("uvicorn").setLevel(logging.INFO)

logger = logging.getLogger("pyquantalpha")
