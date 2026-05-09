"""Tests for X-Request-ID middleware."""
from __future__ import annotations

import re

from fastapi.testclient import TestClient


def test_response_has_request_id_header():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.get("/healthz")

    rid = resp.headers.get("x-request-id")
    assert rid is not None
    # uuid4 hex 形式或 req_<uuid>
    assert re.match(r"^req_[0-9a-f]{32}$", rid), rid


def test_client_request_id_is_propagated():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.get("/healthz", headers={"X-Request-ID": "req_clientside123"})

    assert resp.headers.get("x-request-id") == "req_clientside123"
