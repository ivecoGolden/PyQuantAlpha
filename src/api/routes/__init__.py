# src/api/routes/__init__.py
"""路由模块"""

from . import health, klines, strategy, derivatives

__all__ = ["health", "klines", "strategy", "derivatives"]
