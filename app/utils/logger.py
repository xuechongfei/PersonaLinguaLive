"""Structured JSON logging via structlog, configured from Settings."""
from __future__ import annotations

import logging
import sys
from typing import IO

import structlog

from app.config import Settings


def configure_logging(stream: IO[str] | None = None) -> None:
    """初始化全局 structlog + stdlib logging。idempotent。"""
    settings = Settings()
    level = getattr(logging, settings.log_level)

    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setLevel(level)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=stream or sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "pll") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
