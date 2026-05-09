"""Shared pytest fixtures."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    """每个测试都从干净环境开始,避免互相污染。"""
    for key in list(__import__("os").environ.keys()):
        if key.startswith("PLL_"):
            monkeypatch.delenv(key, raising=False)
    yield
