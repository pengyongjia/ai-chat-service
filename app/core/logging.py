"""
结构化日志配置
使用 loguru 替代 print，支持日志轮转、格式化、级别控制
"""

import sys

from loguru import logger

from app.config import config


def setup_logging():
    """配置全局日志"""
    # 移除默认的 stderr 处理器
    logger.remove()

    # 控制台输出：开发环境使用 DEBUG，生产环境使用 INFO
    log_level = config.LOG_LEVEL.upper()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        colorize=True,
    )

    # 文件输出：按天轮转，保留 7 天
    logger.add(
        "logs/app.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="00:00",  # 每天零点轮转
        retention="7 days",
        encoding="utf-8",
    )

    # 错误日志单独保存
    logger.add(
        "logs/error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )

    return logger


# 全局 logger 实例
log = setup_logging()
