#!/usr/bin/env python3
"""DavyLinks: 统一日志配置"""

from __future__ import annotations

import logging
import sys
import os

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(
    name: str = "davylinks",
    level: str | None = None,
    log_file: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """配置并返回 logger

    Args:
        name: logger 名称，通常为 __name__
        level: 日志级别，默认从 LOG_LEVEL 环境变量读取
        log_file: 日志文件路径，None 则只输出到 stderr
        format_string: 自定义格式，默认使用标准格式

    Returns:
        配置好的 logger 实例
    """
    # 确定日志级别
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)

    # 标准格式
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 创建 formatter
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台 handler（stderr）
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler（可选）
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 默认 logger 供其他模块直接导入使用
default_logger = setup_logging("davylinks")
