# Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap PersonaLinguaLive 全栈骨架,让 `docker run` 启动后:前端能打开、`/healthz` 200、CI 流水线绿,为后续 Phase 2-5 提供可信地基。

**Architecture:** 单容器部署。后端 FastAPI(异步、Pydantic Settings 配置、结构化日志、请求 ID 关联)对外提供 `/api/*` 与 `/healthz`,生产环境同时静态托管前端打包产物。前端 Vite + React 18 + TypeScript + Tailwind,初始仅一个首页组件验证后端可达。

**Tech Stack:**
- 后端:Python 3.12+(`pyproject.toml` 声明 3.14,若无 wheel 可降至 3.12)、FastAPI、uvicorn、Pydantic 2 + pydantic-settings、structlog、httpx、pytest + pytest-asyncio + ruff,包管理 `uv`
- 前端:Vite 5、React 18、TypeScript 5、Tailwind CSS 3、Vitest + @testing-library/react
- 部署:Dockerfile 多阶段构建,GitHub Actions CI

---

## File Structure

```
PersonaLinguaLive/
├── app/                          # 后端 Python 包
│   ├── __init__.py
│   ├── main.py                   # FastAPI 入口,挂路由 + 中间件 + SPA 静态托管
│   ├── config.py                 # Pydantic Settings(.env / 环境变量)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py               # 依赖注入:request_id
│   │   └── health.py             # GET /healthz
│   └── utils/
│       ├── __init__.py
│       └── logger.py             # structlog 配置工厂
├── tests/                        # 后端 pytest
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_logger.py
│   ├── test_health.py
│   └── test_request_id.py
├── frontend/                     # 前端 Vite 项目
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   ├── public/                   # 暂留空
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── styles.css
│       ├── lib/
│       │   └── api.ts            # fetch 封装
│       ├── components/
│       │   └── HealthBadge.tsx
│       └── __tests__/
│           ├── App.test.tsx
│           └── api.test.ts
├── .github/workflows/ci.yml
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore                    # 修改
├── pyproject.toml                # 修改
├── main.py                       # 删除(IDE 模板)
└── README.md                     # 修改 / 新建
```

每个文件单一职责,边界清晰:`main.py` 仅做装配,业务 / 工具按目录分层。

---

## Task 1: 仓库基线整理(删模板、初始化目录与 .gitignore)

**Files:**
- Delete: `main.py`(IDE 默认示例)
- Create: `app/__init__.py`、`app/api/__init__.py`、`app/utils/__init__.py`、`tests/__init__.py`(空文件占位以让目录纳入版本控制)
- Modify/Create: `.gitignore`

- [ ] **Step 1: 删除示例 main.py**

```bash
rm main.py
```

- [ ] **Step 2: 创建后端包目录骨架**

```bash
mkdir -p app/api app/utils tests frontend
touch app/__init__.py app/api/__init__.py app/utils/__init__.py tests/__init__.py
```

- [ ] **Step 3: 写入 .gitignore**

替换或创建 `.gitignore`,内容:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
htmlcov/

# Node / Vite
node_modules/
frontend/dist/
.npm/

# Editor / OS
.idea/
.vscode/
.DS_Store
Thumbs.db

# Env
.env
.env.local
.env.*.local

# Build artifacts
*.log
dist/
build/
```

- [ ] **Step 4: 验证仓库状态**

```bash
git status
```

Expected: 看到 `main.py` 被删除,`app/`、`tests/`、`frontend/` 新目录,`.gitignore` 改动。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: scaffold backend/frontend directory structure"
```

---

## Task 2: 后端依赖与 pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 改写 pyproject.toml**

```toml
[project]
name = "personalingualive"
version = "0.1.0"
description = "An AI-driven English learning Web app: turn objects in any image into talking conversation partners."
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "httpx>=0.27.0",
    "structlog>=24.4.0",
    "python-multipart>=0.0.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra -q"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "RUF"]
ignore = ["E501"]
```

> 注:`requires-python` 从 `>=3.14` 调整为 `>=3.12`,因为 Pydantic 2 等带 Rust 扩展的包在 3.14 wheels 可能尚未齐全。如果你确实要 3.14,可保持原值,但 `uv sync` 失败时回退此值。

- [ ] **Step 2: 同步依赖**

```bash
uv sync --extra dev
```

Expected: 输出 `Resolved N packages` + `Installed`,无错误。

- [ ] **Step 3: 校验 pytest 可用**

```bash
uv run pytest --version
```

Expected: `pytest 8.x.x`。

- [ ] **Step 4: 校验 ruff 可用**

```bash
uv run ruff --version
```

Expected: `ruff 0.7.x`。

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: declare backend dependencies and tooling"
```

---

## Task 3: Pydantic Settings 配置模块(TDD)

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`、`tests/conftest.py`

- [ ] **Step 1: 写 conftest.py(共享 fixture)**

`tests/conftest.py`:

```python
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
```

- [ ] **Step 2: 写失败测试 tests/test_config.py**

```python
"""Tests for app.config.Settings."""
from __future__ import annotations

import pytest


def test_settings_defaults():
    from app.config import Settings

    s = Settings()
    assert s.app_name == "PersonaLinguaLive"
    assert s.environment == "development"
    assert s.cors_allow_origins == ["http://localhost:5173"]
    assert s.frontend_dist_dir == "frontend/dist"
    assert s.log_level == "INFO"


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("PLL_ENVIRONMENT", "production")
    monkeypatch.setenv("PLL_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PLL_CORS_ALLOW_ORIGINS", '["https://pll.example.com"]')

    from app.config import Settings

    s = Settings()
    assert s.environment == "production"
    assert s.log_level == "DEBUG"
    assert s.cors_allow_origins == ["https://pll.example.com"]


def test_settings_invalid_environment(monkeypatch):
    monkeypatch.setenv("PLL_ENVIRONMENT", "staging")  # 不在枚举中

    from app.config import Settings

    with pytest.raises(ValueError):
        Settings()
```

- [ ] **Step 3: 运行测试以确认其失败**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 3 个测试全部 FAIL,因为 `app.config` 不存在(`ModuleNotFoundError`)。

- [ ] **Step 4: 实现 app/config.py**

```python
"""Application settings loaded from environment / .env."""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """所有运行期配置的唯一来源。环境变量前缀 PLL_。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PLL_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PersonaLinguaLive"
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    frontend_dist_dir: str = "frontend/dist"


def get_settings() -> Settings:
    """FastAPI Depends 用的工厂。后续可替换为 lru_cache。"""
    return Settings()
```

- [ ] **Step 5: 运行测试确认通过**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 3 PASSED。

- [ ] **Step 6: Commit**

```bash
git add app/config.py tests/test_config.py tests/conftest.py
git commit -m "feat(config): add Pydantic Settings with env-driven overrides"
```

---

## Task 4: 结构化日志(TDD)

**Files:**
- Create: `app/utils/logger.py`
- Test: `tests/test_logger.py`

- [ ] **Step 1: 写失败测试 tests/test_logger.py**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_logger.py -v
```

Expected: ImportError / ModuleNotFoundError,FAIL。

- [ ] **Step 3: 实现 app/utils/logger.py**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_logger.py -v
```

Expected: 2 PASSED。

- [ ] **Step 5: Commit**

```bash
git add app/utils/logger.py tests/test_logger.py
git commit -m "feat(logging): add structlog JSON logger with level from settings"
```

---

## Task 5: /healthz 端点(TDD)

**Files:**
- Create: `app/api/health.py`、`app/main.py`
- Test: `tests/test_health.py`

- [ ] **Step 1: 写失败测试 tests/test_health.py**

```python
"""Tests for the health endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_returns_ok():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.get("/healthz")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "PersonaLinguaLive"
    assert "version" in body
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_health.py -v
```

Expected: ImportError 因为 `app.main` 不存在。FAIL。

- [ ] **Step 3: 实现 app/api/health.py**

```python
"""GET /healthz — liveness check used by Docker / k8s / curl."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter()


@router.get("/healthz")
def healthz(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
```

- [ ] **Step 4: 实现 app/main.py(最小版,后续 task 扩展)**

```python
"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import health
from app.config import Settings


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 5: 运行测试确认通过**

```bash
uv run pytest tests/test_health.py -v
```

Expected: 1 PASSED。

- [ ] **Step 6: 手动启动一次确认 dev server 能跑**

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Expected: 控制台出现 `Uvicorn running on http://127.0.0.1:8000`。

另开一个终端:

```bash
curl -s http://127.0.0.1:8000/healthz
```

Expected:`{"status":"ok","app":"PersonaLinguaLive","version":"0.1.0","environment":"development"}`。
按 Ctrl+C 停掉 dev server。

- [ ] **Step 7: Commit**

```bash
git add app/main.py app/api/health.py tests/test_health.py
git commit -m "feat(api): add /healthz endpoint and FastAPI application factory"
```

---

## Task 6: 请求 ID 中间件(TDD)

**Files:**
- Create: `app/api/deps.py`
- Modify: `app/main.py`(增加中间件)
- Test: `tests/test_request_id.py`

- [ ] **Step 1: 写失败测试 tests/test_request_id.py**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_request_id.py -v
```

Expected: 2 FAIL(头部不存在或与预期不符)。

- [ ] **Step 3: 实现 app/api/deps.py**

```python
"""HTTP middleware: attach a request_id to every request, expose on response."""
from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    """读 X-Request-ID(若客户端给了),否则生成 req_<uuid hex>。"""

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(self.HEADER)
        rid = incoming if incoming else f"req_{uuid.uuid4().hex}"

        token = structlog.contextvars.bind_contextvars(request_id=rid)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
            del token  # noqa: PLW0603

        response.headers[self.HEADER] = rid
        return response
```

- [ ] **Step 4: 修改 app/main.py 挂中间件**

替换 `create_app` 为:

```python
def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    return app
```

并在文件顶部导入:

```python
from app.api.deps import RequestIdMiddleware
```

- [ ] **Step 5: 运行测试确认通过**

```bash
uv run pytest tests/test_request_id.py -v
```

Expected: 2 PASSED。

- [ ] **Step 6: 跑一次全量测试,确认无回归**

```bash
uv run pytest -v
```

Expected: 所有测试 PASSED(共 8 个左右)。

- [ ] **Step 7: Commit**

```bash
git add app/api/deps.py app/main.py tests/test_request_id.py
git commit -m "feat(api): add X-Request-ID middleware with structlog binding"
```

---

## Task 7: CORS + 静态托管前端(TDD)

**Files:**
- Modify: `app/config.py`(已含 cors_allow_origins,本 task 启用使用)
- Modify: `app/main.py`(增加 CORS + StaticFiles)
- Test: `tests/test_cors_and_static.py`

- [ ] **Step 1: 写失败测试 tests/test_cors_and_static.py**

```python
"""CORS preflight + static SPA fallback."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_cors_allows_dev_origin():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_blocks_unknown_origin():
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.options(
        "/healthz",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI/Starlette 在 origin 不被允许时不附带 ACAO 头
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}


def test_spa_fallback_serves_index_html(tmp_path, monkeypatch):
    dist = tmp_path / "frontend_dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>PLL</title>", encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")

    monkeypatch.setenv("PLL_FRONTEND_DIST_DIR", str(dist))

    from app.main import create_app

    client = TestClient(create_app())

    # 静态资源直出
    asset = client.get("/assets/app.js")
    assert asset.status_code == 200
    assert "console.log" in asset.text

    # 根路径 SPA fallback
    root = client.get("/")
    assert root.status_code == 200
    assert "<title>PLL</title>" in root.text


def test_spa_disabled_when_dist_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("PLL_FRONTEND_DIST_DIR", str(tmp_path / "nonexistent"))

    from app.main import create_app

    client = TestClient(create_app())
    # 此时根路径应是 404,不是崩溃
    resp = client.get("/")
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_cors_and_static.py -v
```

Expected: 多个测试 FAIL,因为 CORS 中间件和静态托管尚未挂载。

- [ ] **Step 3: 修改 app/main.py**

完整替换为:

```python
"""FastAPI application factory."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import health
from app.api.deps import RequestIdMiddleware
from app.config import Settings


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)

    _mount_spa_if_present(app, settings.frontend_dist_dir)
    return app


def _mount_spa_if_present(app: FastAPI, dist_dir: str) -> None:
    """生产模式:把 frontend/dist 挂到 / 与 /assets,并提供 SPA fallback。"""
    dist_path = Path(dist_dir)
    if not (dist_path / "index.html").exists():
        return

    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    index_file = dist_path / "index.html"

    @app.get("/", include_in_schema=False)
    async def _root():
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # 已知 API 路由前缀不应进入 fallback
        if full_path.startswith(("api/", "healthz", "assets/")):
            return FileResponse(index_file, status_code=404)
        target = dist_path / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(index_file)


app = create_app()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_cors_and_static.py -v
```

Expected: 4 PASSED。

- [ ] **Step 5: 全量回归**

```bash
uv run pytest -v
```

Expected: 全部 PASSED。

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_cors_and_static.py
git commit -m "feat(api): add CORS middleware and SPA static fallback"
```

---

## Task 8: 前端 Vite + React + TS 脚手架

**Files:**
- Create: `frontend/package.json`、`frontend/index.html`、`frontend/vite.config.ts`、`frontend/tsconfig.json`、`frontend/tsconfig.node.json`、`frontend/src/main.tsx`、`frontend/src/App.tsx`
- Test: `frontend/src/__tests__/App.test.tsx`

- [ ] **Step 1: 写 package.json**

`frontend/package.json`:

```json
{
  "name": "personalingualive-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src --ext .ts,.tsx"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.0.0",
    "@types/node": "^22.7.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: 安装依赖**

```bash
cd frontend && npm install && cd ..
```

Expected: `added N packages`,无致命错误。

- [ ] **Step 3: 写 tsconfig.json**

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: 写 vite.config.ts**

`frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/healthz': 'http://127.0.0.1:8000',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
  },
});
```

- [ ] **Step 5: 写 index.html**

`frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PersonaLinguaLive</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: 写 src/main.tsx 与 App.tsx**

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

`frontend/src/App.tsx`:

```tsx
export default function App() {
  return (
    <main>
      <h1>PersonaLinguaLive</h1>
      <p>Anything you see can teach you English.</p>
    </main>
  );
}
```

`frontend/src/styles.css`(占位,Task 9 替换为 Tailwind):

```css
body {
  margin: 0;
  font-family: system-ui, sans-serif;
}
```

- [ ] **Step 7: 写测试 setup 与 App 测试**

`frontend/src/__tests__/setup.ts`:

```typescript
import '@testing-library/jest-dom/vitest';
```

`frontend/src/__tests__/App.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('App', () => {
  it('renders the product name', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('PersonaLinguaLive');
  });

  it('renders the tagline', () => {
    render(<App />);
    expect(
      screen.getByText(/Anything you see can teach you English/i)
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 8: 跑测试**

```bash
cd frontend && npm test && cd ..
```

Expected: `Test Files 1 passed (1) · Tests 2 passed (2)`。

- [ ] **Step 9: 跑一次 dev server 手动验证**

```bash
cd frontend && npm run dev
```

Expected: 控制台 `VITE v5.x ready in N ms · Local: http://localhost:5173/`。
浏览器打开,确认显示标题。Ctrl+C 停掉。

- [ ] **Step 10: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): scaffold Vite + React + TS with first vitest passing"
```

---

## Task 9: Tailwind CSS 接入

**Files:**
- Modify: `frontend/package.json`(增加 tailwind 相关 devDependencies)
- Create: `frontend/tailwind.config.js`、`frontend/postcss.config.js`
- Modify: `frontend/src/styles.css`、`frontend/src/App.tsx`

- [ ] **Step 1: 安装 Tailwind**

```bash
cd frontend && npm install -D tailwindcss@^3.4.0 postcss@^8.4.0 autoprefixer@^10.4.0 && cd ..
```

Expected: `added 3 packages`。

- [ ] **Step 2: 写 tailwind.config.js**

`frontend/tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 3: 写 postcss.config.js**

`frontend/postcss.config.js`:

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 4: 重写 src/styles.css**

`frontend/src/styles.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: 更新 App.tsx 用 Tailwind**

`frontend/src/App.tsx`:

```tsx
export default function App() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-slate-50 text-slate-900">
      <h1 className="text-3xl font-bold">PersonaLinguaLive</h1>
      <p className="mt-2 text-slate-600">
        Anything you see can teach you English.
      </p>
    </main>
  );
}
```

- [ ] **Step 6: 跑测试确认无回归**

```bash
cd frontend && npm test && cd ..
```

Expected: 2 passed,Tailwind class 不影响 RTL 断言。

- [ ] **Step 7: 跑 dev server,目视检查样式生效**

```bash
cd frontend && npm run dev
```

打开浏览器,确认背景灰、标题加粗居中。Ctrl+C 停掉。

- [ ] **Step 8: Commit**

```bash
cd ..
git add frontend/package.json frontend/package-lock.json frontend/tailwind.config.js frontend/postcss.config.js frontend/src/styles.css frontend/src/App.tsx
git commit -m "feat(frontend): integrate Tailwind CSS for utility-first styling"
```

---

## Task 10: 前端 API 客户端 + HealthBadge(TDD)

**Files:**
- Create: `frontend/src/lib/api.ts`、`frontend/src/components/HealthBadge.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/__tests__/api.test.ts`、`frontend/src/__tests__/HealthBadge.test.tsx`

- [ ] **Step 1: 写失败测试 api.test.ts**

`frontend/src/__tests__/api.test.ts`:

```typescript
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchHealth } from '../lib/api';

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe('fetchHealth', () => {
  it('returns parsed payload on 200', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'ok',
        app: 'PersonaLinguaLive',
        version: '0.1.0',
        environment: 'development',
      }),
    } as unknown as Response);

    const result = await fetchHealth();
    expect(result.status).toBe('ok');
    expect(result.version).toBe('0.1.0');
  });

  it('throws on non-2xx', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({}),
    } as unknown as Response);

    await expect(fetchHealth()).rejects.toThrow(/503/);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/__tests__/api.test.ts && cd ..
```

Expected: FAIL(模块不存在)。

- [ ] **Step 3: 实现 lib/api.ts**

`frontend/src/lib/api.ts`:

```typescript
export interface HealthPayload {
  status: 'ok';
  app: string;
  version: string;
  environment: 'development' | 'production' | 'test';
}

const BASE_URL = import.meta.env.VITE_API_BASE ?? '';

export async function fetchHealth(): Promise<HealthPayload> {
  const resp = await fetch(`${BASE_URL}/healthz`);
  if (!resp.ok) {
    throw new Error(`Health check failed with status ${resp.status}`);
  }
  return (await resp.json()) as HealthPayload;
}
```

- [ ] **Step 4: 跑 api 测试确认通过**

```bash
cd frontend && npm test -- --run src/__tests__/api.test.ts && cd ..
```

Expected: 2 passed。

- [ ] **Step 5: 写 HealthBadge 组件失败测试**

`frontend/src/__tests__/HealthBadge.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HealthBadge from '../components/HealthBadge';

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe('HealthBadge', () => {
  it('shows checking → ok when API responds 200', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'ok',
        app: 'PersonaLinguaLive',
        version: '0.1.0',
        environment: 'development',
      }),
    } as unknown as Response);

    render(<HealthBadge />);

    expect(screen.getByText(/checking/i)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/v0\.1\.0/)).toBeInTheDocument()
    );
    expect(screen.getByText(/development/)).toBeInTheDocument();
  });

  it('shows error state when API fails', async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({}),
    } as unknown as Response);

    render(<HealthBadge />);
    await waitFor(() =>
      expect(screen.getByText(/offline|unavailable/i)).toBeInTheDocument()
    );
  });
});
```

- [ ] **Step 6: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/__tests__/HealthBadge.test.tsx && cd ..
```

Expected: FAIL,组件不存在。

- [ ] **Step 7: 实现 components/HealthBadge.tsx**

`frontend/src/components/HealthBadge.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { fetchHealth, type HealthPayload } from '../lib/api';

type State =
  | { kind: 'checking' }
  | { kind: 'ok'; data: HealthPayload }
  | { kind: 'error'; message: string };

export default function HealthBadge() {
  const [state, setState] = useState<State>({ kind: 'checking' });

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((data) => {
        if (!cancelled) setState({ kind: 'ok', data });
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'Unknown error';
          setState({ kind: 'error', message: msg });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === 'checking') {
    return (
      <span className="inline-flex items-center rounded-full bg-slate-200 px-3 py-1 text-xs text-slate-700">
        Checking backend…
      </span>
    );
  }
  if (state.kind === 'error') {
    return (
      <span
        className="inline-flex items-center rounded-full bg-rose-100 px-3 py-1 text-xs text-rose-700"
        title={state.message}
      >
        Backend offline / unavailable
      </span>
    );
  }
  const { app, version, environment } = state.data;
  return (
    <span className="inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-xs text-emerald-800">
      {app} v{version} · {environment}
    </span>
  );
}
```

- [ ] **Step 8: 接入 App.tsx**

`frontend/src/App.tsx`:

```tsx
import HealthBadge from './components/HealthBadge';

export default function App() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-slate-50 text-slate-900">
      <h1 className="text-3xl font-bold">PersonaLinguaLive</h1>
      <p className="mt-2 text-slate-600">
        Anything you see can teach you English.
      </p>
      <div className="mt-6">
        <HealthBadge />
      </div>
    </main>
  );
}
```

- [ ] **Step 9: 修改 App.test.tsx 不被新增的 HealthBadge 调用 fetch 影响**

`frontend/src/__tests__/App.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      status: 'ok',
      app: 'PersonaLinguaLive',
      version: '0.1.0',
      environment: 'development',
    }),
  } as unknown as Response);
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe('App', () => {
  it('renders the product name', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('PersonaLinguaLive');
  });

  it('renders the tagline', () => {
    render(<App />);
    expect(
      screen.getByText(/Anything you see can teach you English/i)
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 10: 跑全部前端测试**

```bash
cd frontend && npm test && cd ..
```

Expected: 全部 PASSED(6 tests across 3 files)。

- [ ] **Step 11: 手动联调:同时启后端 + 前端,验证 HealthBadge 在浏览器里变绿**

终端 A:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

终端 B:

```bash
cd frontend && npm run dev
```

浏览器打开 `http://localhost:5173/`,顶部应有绿色 badge,显示 `PersonaLinguaLive v0.1.0 · development`。
两个终端都 Ctrl+C 停掉。

- [ ] **Step 12: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/components/HealthBadge.tsx frontend/src/App.tsx frontend/src/__tests__/
git commit -m "feat(frontend): wire HealthBadge to backend /healthz with vitest coverage"
```

---

## Task 11: Dockerfile 多阶段构建

**Files:**
- Create: `Dockerfile`、`.dockerignore`

- [ ] **Step 1: 写 .dockerignore**

`.dockerignore`:

```
.git
.idea
.vscode
__pycache__
*.pyc
.venv
node_modules
frontend/dist
frontend/node_modules
.pytest_cache
.ruff_cache
.mypy_cache
htmlcov
*.log
.env
.env.*
docs
tests
```

- [ ] **Step 2: 写 Dockerfile**

`Dockerfile`:

```dockerfile
# ===== Stage 1: Build frontend =====
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ===== Stage 2: Python runtime =====
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLL_ENVIRONMENT=production \
    PLL_FRONTEND_DIST_DIR=/app/frontend/dist

WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv==0.5.0

# 先拷依赖文件做依赖层缓存
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# 拷代码
COPY app/ ./app/

# 拷前端构建产物
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 本地构建镜像**

```bash
docker build -t pll:dev .
```

Expected: 构建成功,最终输出 `Successfully tagged pll:dev`。

- [ ] **Step 4: 启动容器**

```bash
docker run --rm -p 8000:8000 --name pll-test pll:dev
```

Expected: 控制台出现 `Uvicorn running on http://0.0.0.0:8000`。

- [ ] **Step 5: 验证健康 + 前端**

另开终端:

```bash
curl -s http://127.0.0.1:8000/healthz
```

Expected:`{"status":"ok","app":"PersonaLinguaLive","version":"0.1.0","environment":"production"}`(注意 environment=production)。

```bash
curl -sI http://127.0.0.1:8000/
```

Expected:`HTTP/1.1 200 OK`,`content-type: text/html`。

按 Ctrl+C 停掉容器。

- [ ] **Step 6: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "build: add multi-stage Dockerfile (frontend + python runtime)"
```

---

## Task 12: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: 写 ci.yml**

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  backend:
    name: Backend (lint + test)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        run: pip install uv==0.5.0

      - name: Sync dependencies
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check app tests

      - name: Test
        run: uv run pytest -v

  frontend:
    name: Frontend (build + test)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install
        run: npm ci

      - name: Type check
        run: npx tsc -b --noEmit

      - name: Test
        run: npm test

      - name: Build
        run: npm run build

  docker:
    name: Docker build (smoke)
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t pll:ci .
      - name: Run container and curl healthz
        run: |
          docker run -d --name pll-ci -p 8000:8000 pll:ci
          for i in 1 2 3 4 5; do
            if curl -sf http://127.0.0.1:8000/healthz; then exit 0; fi
            sleep 2
          done
          docker logs pll-ci
          exit 1
```

- [ ] **Step 2: 本地 lint 一遍,确保 CI 不会因为格式失败**

```bash
uv run ruff check app tests
```

Expected: `All checks passed!`(若有问题先 `uv run ruff check --fix app tests` 自动修复)。

- [ ] **Step 3: 本地全量测试一遍**

```bash
uv run pytest -v && (cd frontend && npm test) && cd ..
```

Expected: 后端 + 前端全绿。

- [ ] **Step 4: Commit + push,确认 GitHub Actions 跑通**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions for backend, frontend, and docker smoke"
git push
```

到 GitHub 仓库 Actions 标签确认三个 job 全绿。如有 job 失败,根据日志定位、本地修复、再 commit + push。

---

## Task 13: README + .env.example

**Files:**
- Create / Modify: `README.md`、`.env.example`

- [ ] **Step 1: 写 .env.example**

`.env.example`:

```env
# Application
PLL_ENVIRONMENT=development
PLL_LOG_LEVEL=INFO

# CORS(JSON 数组字面量)
PLL_CORS_ALLOW_ORIGINS=["http://localhost:5173"]

# 前端打包产物路径(生产模式下被 FastAPI 静态托管)
PLL_FRONTEND_DIST_DIR=frontend/dist
```

- [ ] **Step 2: 写 README.md**

`README.md`:

```markdown
# PersonaLinguaLive

> Anything you see can teach you English.

一款 Web 端 AI 英语学习应用:用户上传一张图片,图中物体被 AI 拟人化后可点击对话,边玩边学。

## 文档导航
- [产品需求文档(PRD)](docs/prd/2026-05-09-personalingualive-prd.md)
- [技术设计文档](docs/design/2026-05-09-personalingualive-design.md)
- [实现计划路线图](docs/plans/README.md)

## 本地开发

### 前置依赖
- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/)

### 后端

\`\`\`bash
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
\`\`\`

### 前端

\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

打开浏览器访问 http://localhost:5173,顶部 HealthBadge 应显示绿色 `PersonaLinguaLive v0.1.0 · development`。

## 测试

\`\`\`bash
# 后端
uv run pytest -v
# 前端
cd frontend && npm test
\`\`\`

## Docker

\`\`\`bash
docker build -t pll:dev .
docker run --rm -p 8000:8000 pll:dev
\`\`\`

访问 http://localhost:8000。

## 目录结构

\`\`\`
app/        FastAPI 后端
frontend/   Vite + React 前端
tests/      后端测试
docs/       PRD / 设计 / 计划文档
\`\`\`
```

> 注:上面 README 中的代码块在文件里写 ``` 不要带反斜杠;我这里反斜杠仅用于在本计划文件中转义。

- [ ] **Step 3: 复制 .env.example 到 .env 并验证启动**

```bash
cp .env.example .env
uv run uvicorn app.main:app --port 8000
```

Expected: 启动正常,Ctrl+C 停掉。

- [ ] **Step 4: Commit**

```bash
git add README.md .env.example
git commit -m "docs: add README and .env.example"
```

---

## Phase 1 验收清单

- [ ] `uv run pytest -v` 全部 PASSED(预期 ~10 测试)
- [ ] `cd frontend && npm test` 全部 PASSED(预期 6 测试)
- [ ] `uv run ruff check app tests` 通过
- [ ] 本地启 dev 后端 + dev 前端,浏览器访问 `http://localhost:5173`,HealthBadge 绿色显示版本与环境
- [ ] `docker build -t pll:dev . && docker run --rm -p 8000:8000 pll:dev` 容器内 `/healthz` 返回 environment=production
- [ ] GitHub Actions 三个 job(backend / frontend / docker)全绿
- [ ] 仓库根目录有 PRD、设计文档、Phase 1 计划、README,目录干净

满足以上即视为 Phase 1 完成,可进入 Phase 2(视觉链路:M1 + M2 + M3)。

---

## Phase 1 → Phase 2 衔接备注

进入 Phase 2 时,以下设计在 Phase 1 已铺好但不会被前端用到,Phase 2 直接继承:
- `RequestIdMiddleware` 已挂载,Phase 2 业务调用 AI 适配层时,`structlog.contextvars` 里 request_id 自动可用
- `Settings` 模式已成熟,Phase 2 新增 AI key、模型名等只需扩 `app/config.py` 字段
- `app/api/__init__.py` 已是 router 聚合点,新端点照 `health.py` 模式加即可
- 前端 Vite 代理已配 `/api`,Phase 2 调 `/api/vision/analyze` 无 CORS 烦恼

Phase 2 计划将在本 Phase 验收通过后再写,文件名:`docs/plans/2026-05-09-phase-2-vision-pipeline.md`。
