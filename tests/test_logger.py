"""Tests for app.utils.logger."""
from __future__ import annotations

import io
import json
import logging


def test_configure_logger_writes_json(monkeypatch):
    monkeypatch.setenv("PLL_LOG_LEVEL", "INFO")

    from app.utils.logger import configure_logging, get_logger

    stream = io.StringIO()
    configure_logging(stream=stream)

    log = get_logger("pll.test")
    log.info("hello", request_id="req_abc", endpoint="/healthz")

    line = stream.getvalue().strip().splitlines()[-1]
    record = json.loads(line)

    assert record["event"] == "hello"
    assert record["request_id"] == "req_abc"
    assert record["endpoint"] == "/healthz"
    assert record["level"] == "info"
    assert "timestamp" in record


def test_configure_logger_respects_level(monkeypatch):
    monkeypatch.setenv("PLL_LOG_LEVEL", "WARNING")

    from app.utils.logger import configure_logging, get_logger

    stream = io.StringIO()
    configure_logging(stream=stream)

    log = get_logger("pll.test")
    log.info("should-be-filtered")
    log.warning("should-appear")

    output = stream.getvalue()
    assert "should-be-filtered" not in output
    assert "should-appear" in output


def teardown_function(_):
    # 防止 caplog/structlog 的 handler 残留泄漏到下个测试
    logging.getLogger().handlers.clear()
