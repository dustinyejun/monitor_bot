"""
pytest配置文件
"""
import pytest


def pytest_addoption(parser):
    """添加pytest命令行选项"""
    parser.addoption(
        "--run-real-api",
        action="store_true",
        default=False,
        help="运行需要真实API连接的测试"
    )


def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", "real_api: 标记需要真实API连接的测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试项收集"""
    if config.getoption("--run-real-api"):
        # 如果指定了--run-real-api，则运行所有测试
        return
    
    skip_real_api = pytest.mark.skip(reason="需要 --run-real-api 选项才能运行")
    for item in items:
        if "real_api" in item.keywords:
            item.add_marker(skip_real_api)