# tests/conftest.py
"""pytest 全局配置"""

import pytest


def pytest_addoption(parser):
    """添加自定义命令行选项"""
    parser.addoption(
        "--run-benchmark",
        action="store_true",
        default=False,
        help="运行性能基准测试 (需要网络)"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="运行集成测试 (需要网络)"
    )


def pytest_configure(config):
    """添加自定义标记"""
    config.addinivalue_line(
        "markers", "benchmark: 性能基准测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试 (需要网络)"
    )


def pytest_collection_modifyitems(config, items):
    """根据命令行选项跳过测试"""
    if not config.getoption("--run-benchmark"):
        skip_benchmark = pytest.mark.skip(reason="需要 --run-benchmark 参数")
        for item in items:
            if "benchmark" in item.keywords:
                item.add_marker(skip_benchmark)
    
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="需要 --run-integration 参数")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
