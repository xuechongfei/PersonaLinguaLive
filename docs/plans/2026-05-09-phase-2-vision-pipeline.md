# Phase 2: Vision Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通"上传图片 → 内容安全检查 → 显示可点击热区"端到端链路,实现 PRD M1(图片上传)+ M2(内容安全过滤)+ M3(物体检测与热区),Phase 2 结束后可在浏览器演示完整视觉链路。

**Architecture:** 后端新增 `POST /api/vision/analyze` 端点,内部分层为 API 路由 → `VisionService` 编排 → `VisionAdapter` Protocol(Fake/OpenAI 双实现,工厂按 `Settings` 选)→ `SafetyGuard` 二次判定。错误统一走 `app/errors.py` + 全局异常处理器。前端按 `Home → Studio` 两态切换:`UploadZone` 收文件、客户端预检与压缩、调 `analyzeImage`,拿到 objects 后切到 `Studio` 渲染 `ImageCanvas + HotspotOverlay`,点击热区弹 `PersonaPlaceholderPanel` 占位面板。

**Tech Stack:**
- 后端新增依赖:`respx>=0.21.0`(httpx mock,dev only)。Vision/OpenAI 调用直接复用已装好的 `httpx`,不引入 `openai` SDK
- 前端新增依赖:无(`<input type=file>` + drag/drop + Canvas 压缩均为浏览器原生)
- 已沿用:FastAPI、Pydantic 2、structlog、Vite + React + TS + Tailwind、Vitest + Testing Library

**关键设计假设(沿用 PRD/Design v0.1)**
- Vision 适配层默认 provider=`fake`,有 `PLL_OPENAI_API_KEY` 时可切 `openai` 跑真实流程
- 上传仅支持 JPG/PNG/WebP(HEIC 留 V2);拍照延后到 Phase 3 或 V2
- 客户端先压缩到最长边 ≤1600px JPEG 再上传;后端硬限制 10MB
- 热区点击 Phase 2 仅弹占位面板,真实对话在 Phase 3 接入

---

## File Structure

```
PersonaLinguaLive/
├── app/
│   ├── adapters/                          # 新增
│   │   ├── __init__.py
│   │   ├── factory.py                     # build_vision_adapter(settings)
│   │   └── vision/
│   │       ├── __init__.py
│   │       ├── base.py                    # VisionAdapter Protocol
│   │       ├── fake.py                    # FakeVisionAdapter
│   │       └── openai_vision.py           # OpenAIVisionAdapter
│   ├── api/
│   │   └── vision.py                      # 新增: POST /api/vision/analyze
│   ├── errors.py                          # 新增: PLLError 体系 + 全局 handler
│   ├── prompts/                           # 新增
│   │   ├── __init__.py
│   │   └── vision_safety.py
│   ├── schemas/                           # 新增
│   │   ├── __init__.py
│   │   └── vision.py
│   ├── services/                          # 新增
│   │   ├── __init__.py
│   │   ├── safety_guard.py
│   │   └── vision_service.py
│   ├── utils/
│   │   └── ratelimit.py                   # 新增
│   ├── config.py                          # 修改
│   └── main.py                            # 修改
├── tests/
│   ├── fixtures/                          # 新增
│   │   ├── __init__.py
│   │   └── images.py
│   ├── test_errors.py                     # 新增
│   ├── test_fake_vision_adapter.py        # 新增
│   ├── test_openai_vision_adapter.py      # 新增
│   ├── test_ratelimit.py                  # 新增
│   ├── test_safety_guard.py               # 新增
│   ├── test_vision_endpoint.py            # 新增
│   ├── test_vision_factory.py             # 新增
│   ├── test_vision_prompt.py              # 新增
│   ├── test_vision_schemas.py             # 新增
│   └── test_vision_service.py             # 新增
├── frontend/
│   └── src/
│       ├── components/                   # 新增组件直接放 components/ 顶层
│       │   ├── ImageCanvas.tsx
│       │   ├── HotspotOverlay.tsx
│       │   ├── PersonaPlaceholderPanel.tsx
│       │   └── UploadZone.tsx
│       ├── lib/
│       │   ├── api.ts                     # 修改
│       │   ├── image/
│       │   │   └── compress.ts            # 新增
│       │   └── safety/
│       │       └── preUpload.ts           # 新增
│       ├── pages/                         # 新增
│       │   ├── HomePage.tsx
│       │   └── StudioPage.tsx
│       ├── App.tsx                        # 修改
│       └── __tests__/                     # 新增多个测试
├── .env.example                           # 修改
└── pyproject.toml                         # 修改
```

---

## Task 1: 后端依赖与配置扩展

**Files:**
- Modify: `pyproject.toml`(dev dep `respx`)
- Modify: `app/config.py`(新增 AI / 上传 / 限流字段 + provider 校验)
- Modify: `tests/test_config.py`(追加 5 个测试)

- [ ] **Step 1: 改 pyproject.toml,dev 增加 respx**

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.7.0",
    "respx>=0.21.0",
]
```

- [ ] **Step 2: 同步依赖**

```bash
uv sync --extra dev
```

Expected: `Resolved N packages` + `Installed`。

- [ ] **Step 3: 写失败测试 tests/test_config.py(末尾追加)**

```python
def test_settings_ai_defaults():
    from app.config import Settings

    s = Settings()
    assert s.ai_vision_provider == "fake"
    assert s.openai_api_key is None
    assert s.openai_base_url == "https://api.openai.com/v1"
    assert s.openai_model_vision == "gpt-4o"
    assert s.openai_request_timeout_s == 30.0


def test_settings_upload_defaults():
    from app.config import Settings

    s = Settings()
    assert s.upload_max_bytes == 10 * 1024 * 1024
    assert s.upload_allowed_mime == ["image/jpeg", "image/png", "image/webp"]


def test_settings_rate_limit_defaults():
    from app.config import Settings

    s = Settings()
    assert s.rate_limit_vision_per_min == 6


def test_settings_openai_provider_requires_api_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "openai")
    monkeypatch.delenv("PLL_OPENAI_API_KEY", raising=False)

    from app.config import Settings

    with pytest.raises(ValueError, match="PLL_OPENAI_API_KEY"):
        Settings()


def test_settings_openai_provider_accepts_api_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "openai")
    monkeypatch.setenv("PLL_OPENAI_API_KEY", "sk-test-123")

    from app.config import Settings

    s = Settings()
    assert s.ai_vision_provider == "openai"
    assert s.openai_api_key.get_secret_value() == "sk-test-123"
```

- [ ] **Step 4: 跑测试确认失败**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 5 个新测试 FAIL。

- [ ] **Step 5: 实现 app/config.py(完整替换)**

```python
"""Application settings loaded from environment / .env."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, model_validator
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

    # === AI 适配层 ===
    ai_vision_provider: Literal["fake", "openai"] = "fake"
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model_vision: str = "gpt-4o"
    openai_request_timeout_s: float = 30.0

    # === 上传约束 ===
    upload_max_bytes: int = 10 * 1024 * 1024  # 10 MiB
    upload_allowed_mime: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )

    # === 限流(单实例内存桶,IP 维度)===
    rate_limit_vision_per_min: int = 6

    @model_validator(mode="after")
    def _validate_provider_credentials(self) -> "Settings":
        if self.ai_vision_provider == "openai" and self.openai_api_key is None:
            raise ValueError(
                "PLL_OPENAI_API_KEY is required when AI_VISION_PROVIDER=openai"
            )
        return self


def get_settings() -> Settings:
    """FastAPI Depends 用的工厂。"""
    return Settings()
```

- [ ] **Step 6: 跑测试确认通过**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 8 PASSED。

- [ ] **Step 7: 全量回归**

```bash
uv run pytest -v
```

Expected: 所有 Phase 1 测试仍 PASSED。

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock app/config.py tests/test_config.py
git commit -m "feat(config): add AI provider, upload, and rate-limit settings"
```

---

## Task 2: 错误模型与全局异常处理(TDD)

**Files:**
- Create: `app/errors.py`
- Modify: `app/main.py`(注册 exception handler)
- Test: `tests/test_errors.py`

- [ ] **Step 1: 写失败测试 tests/test_errors.py**

```python
"""Tests for app.errors and global exception handler."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app_with_routes() -> FastAPI:
    from app.errors import (
        InvalidInputError,
        PayloadTooLargeError,
        PLLError,
        RateLimitedError,
        UnsafeImageError,
        UnsupportedMediaError,
        UpstreamFailureError,
        UpstreamTimeoutError,
        register_exception_handlers,
    )

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/{kind}")
    def _raise(kind: str):
        if kind == "invalid":
            raise InvalidInputError("missing field 'image'")
        if kind == "too-large":
            raise PayloadTooLargeError("file is 12MB, max 10MB")
        if kind == "unsupported":
            raise UnsupportedMediaError("image/gif")
        if kind == "unsafe":
            raise UnsafeImageError(reasons=["face_detected"])
        if kind == "rate":
            raise RateLimitedError(retry_after_s=42)
        if kind == "upstream-fail":
            raise UpstreamFailureError(provider="openai")
        if kind == "upstream-timeout":
            raise UpstreamTimeoutError(provider="openai")
        if kind == "base":
            raise PLLError("INTERNAL_ERROR", "boom", http_status=500)
        return {"ok": True}

    return app


def test_invalid_input_returns_400():
    resp = TestClient(_build_app_with_routes()).get("/raise/invalid")
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_INPUT"


def test_payload_too_large_returns_413():
    resp = TestClient(_build_app_with_routes()).get("/raise/too-large")
    assert resp.status_code == 413
    assert resp.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_unsupported_media_returns_415():
    resp = TestClient(_build_app_with_routes()).get("/raise/unsupported")
    assert resp.status_code == 415
    assert resp.json()["code"] == "UNSUPPORTED_MEDIA"


def test_unsafe_image_returns_422_with_reasons():
    resp = TestClient(_build_app_with_routes()).get("/raise/unsafe")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "UNSAFE_IMAGE"
    assert body["details"]["reject_reasons"] == ["face_detected"]


def test_rate_limited_returns_429_with_retry_after_header():
    resp = TestClient(_build_app_with_routes()).get("/raise/rate")
    assert resp.status_code == 429
    assert resp.json()["code"] == "RATE_LIMITED"
    assert resp.headers.get("retry-after") == "42"


def test_upstream_failure_returns_502():
    resp = TestClient(_build_app_with_routes()).get("/raise/upstream-fail")
    assert resp.status_code == 502
    assert resp.json()["code"] == "UPSTREAM_FAILURE"
    assert resp.json()["details"]["provider"] == "openai"


def test_upstream_timeout_returns_504():
    resp = TestClient(_build_app_with_routes()).get("/raise/upstream-timeout")
    assert resp.status_code == 504
    assert resp.json()["code"] == "UPSTREAM_TIMEOUT"


def test_base_pll_error_returns_custom_status():
    resp = TestClient(_build_app_with_routes()).get("/raise/base")
    assert resp.status_code == 500
    assert resp.json()["code"] == "INTERNAL_ERROR"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_errors.py -v
```

Expected: ImportError(`app.errors` 不存在)。

- [ ] **Step 3: 实现 app/errors.py**

```python
"""Domain errors and FastAPI exception handlers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class PLLError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 500,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        self.headers = headers or {}


class InvalidInputError(PLLError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_INPUT", message, http_status=400)


class PayloadTooLargeError(PLLError):
    def __init__(self, message: str) -> None:
        super().__init__("PAYLOAD_TOO_LARGE", message, http_status=413)


class UnsupportedMediaError(PLLError):
    def __init__(self, mime: str) -> None:
        super().__init__(
            "UNSUPPORTED_MEDIA",
            f"unsupported media type: {mime}",
            http_status=415,
            details={"mime": mime},
        )


class UnsafeImageError(PLLError):
    def __init__(self, *, reasons: list[str]) -> None:
        super().__init__(
            "UNSAFE_IMAGE",
            "image rejected by content safety check",
            http_status=422,
            details={"reject_reasons": list(reasons)},
        )


class RateLimitedError(PLLError):
    def __init__(self, *, retry_after_s: int) -> None:
        super().__init__(
            "RATE_LIMITED",
            "rate limit exceeded",
            http_status=429,
            details={"retry_after_s": retry_after_s},
            headers={"Retry-After": str(retry_after_s)},
        )


class UpstreamFailureError(PLLError):
    def __init__(self, *, provider: str, message: str = "upstream provider failed") -> None:
        super().__init__(
            "UPSTREAM_FAILURE",
            message,
            http_status=502,
            details={"provider": provider},
        )


class UpstreamTimeoutError(PLLError):
    def __init__(self, *, provider: str) -> None:
        super().__init__(
            "UPSTREAM_TIMEOUT",
            "upstream provider timed out",
            http_status=504,
            details={"provider": provider},
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PLLError)
    async def _pll_error_handler(_request: Request, exc: PLLError) -> JSONResponse:
        body = {"code": exc.code, "message": exc.message, "details": exc.details}
        return JSONResponse(body, status_code=exc.http_status, headers=exc.headers)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
uv run pytest tests/test_errors.py -v
```

Expected: 8 PASSED。

- [ ] **Step 5: 在 app/main.py 注册 handler**

把 `create_app()` 中 `app.add_middleware(RequestIdMiddleware)` 这一行后面追加:

```python
    from app.errors import register_exception_handlers

    register_exception_handlers(app)
```

- [ ] **Step 6: 全量回归**

```bash
uv run pytest -v
```

Expected: 全部 PASSED。

- [ ] **Step 7: Commit**

```bash
git add app/errors.py app/main.py tests/test_errors.py
git commit -m "feat(errors): add PLLError hierarchy and global exception handler"
```

---

## Task 3: Vision Pydantic schemas(TDD)

**Files:**
- Create: `app/schemas/__init__.py`、`app/schemas/vision.py`
- Test: `tests/test_vision_schemas.py`

- [ ] **Step 1: 写失败测试 tests/test_vision_schemas.py**

```python
"""Tests for app.schemas.vision."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_bbox_accepts_normalized_floats():
    from app.schemas.vision import BBox

    b = BBox(x=0.1, y=0.2, w=0.3, h=0.4)
    assert b.x == 0.1
    assert b.h == 0.4


def test_bbox_rejects_out_of_range():
    from app.schemas.vision import BBox

    with pytest.raises(ValidationError):
        BBox(x=-0.1, y=0, w=0.5, h=0.5)
    with pytest.raises(ValidationError):
        BBox(x=0, y=0, w=1.5, h=0.5)


def test_detected_object_round_trip():
    from app.schemas.vision import BBox, DetectedObject

    obj = DetectedObject(
        id="o_1",
        label="cupcake",
        bbox=BBox(x=0.1, y=0.1, w=0.2, h=0.2),
        confidence=0.9,
        persona_seed="sweet baker",
    )
    data = obj.model_dump()
    assert data["id"] == "o_1"
    assert data["confidence"] == 0.9
    assert data["bbox"] == {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}


def test_detected_object_rejects_confidence_out_of_range():
    from app.schemas.vision import BBox, DetectedObject

    with pytest.raises(ValidationError):
        DetectedObject(
            id="o_1",
            label="x",
            bbox=BBox(x=0, y=0, w=0.1, h=0.1),
            confidence=1.2,
        )


def test_vision_result_defaults():
    from app.schemas.vision import VisionResult

    r = VisionResult(is_safe=True)
    assert r.is_safe is True
    assert r.reject_reasons == []
    assert r.scene_summary == ""
    assert r.objects == []


def test_vision_analyze_response_shape():
    from app.schemas.vision import VisionAnalyzeResponse

    payload = VisionAnalyzeResponse(
        request_id="req_abc",
        is_safe=True,
        reject_reasons=[],
        scene_summary="kitchen",
        objects=[],
    )
    dumped = payload.model_dump()
    assert dumped["request_id"] == "req_abc"
    assert dumped["scene_summary"] == "kitchen"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_vision_schemas.py -v
```

Expected: ImportError。

- [ ] **Step 3: 实现 app/schemas/__init__.py**

```python
"""Pydantic schemas for API contracts."""
```

- [ ] **Step 4: 实现 app/schemas/vision.py**

```python
"""Pydantic models for /api/vision/analyze and adapter results."""
from __future__ import annotations

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """Normalized bounding box (top-left origin, all values in [0, 1])."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(ge=0.0, le=1.0)
    h: float = Field(ge=0.0, le=1.0)


class DetectedObject(BaseModel):
    id: str
    label: str
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0)
    persona_seed: str | None = None


class VisionResult(BaseModel):
    is_safe: bool
    reject_reasons: list[str] = Field(default_factory=list)
    scene_summary: str = ""
    objects: list[DetectedObject] = Field(default_factory=list)


class VisionAnalyzeResponse(BaseModel):
    request_id: str
    is_safe: bool
    reject_reasons: list[str] = Field(default_factory=list)
    scene_summary: str = ""
    objects: list[DetectedObject] = Field(default_factory=list)
```

- [ ] **Step 5: 跑测试确认通过**

```bash
uv run pytest tests/test_vision_schemas.py -v
```

Expected: 5 PASSED。

- [ ] **Step 6: Commit**

```bash
git add app/schemas/ tests/test_vision_schemas.py
git commit -m "feat(schemas): add VisionResult and DetectedObject Pydantic models"
```

---

## Task 4: VisionAdapter Protocol + FakeVisionAdapter(TDD)

**Files:**
- Create: `app/adapters/__init__.py`、`app/adapters/vision/__init__.py`、`app/adapters/vision/base.py`、`app/adapters/vision/fake.py`
- Create: `tests/fixtures/__init__.py`、`tests/fixtures/images.py`
- Test: `tests/test_fake_vision_adapter.py`

**Why FakeVisionAdapter:** CI 与本地无 `OPENAI_API_KEY` 时也能跑端到端;同时给上层 service / endpoint 提供可注入替身。Fake 通过特殊 byte prefix 触发不同分支;真实 JPEG/PNG 不会包含这些前缀,生产调用永远走 default safe 分支。

- [ ] **Step 1: 写 tests/fixtures/__init__.py(空)**

```python
"""Shared fixtures for tests."""
```

- [ ] **Step 2: 写 tests/fixtures/images.py**

```python
"""Helpers to build test image byte strings."""
from __future__ import annotations

# 真实 1x1 px PNG(透明)。FakeVisionAdapter 会落入 'safe' 分支。
_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfa\xcf"
    b"\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def safe_png_bytes() -> bytes:
    return _PNG_1X1


def fake_face_bytes() -> bytes:
    return b"PLL_FAKE_FACE\x00" + b"\x00" * 64


def fake_nsfw_bytes() -> bytes:
    return b"PLL_FAKE_NSFW\x00" + b"\x00" * 64


def fake_text_bytes() -> bytes:
    return b"PLL_FAKE_TEXT\x00" + b"\x00" * 64


def fake_unclear_bytes() -> bytes:
    return b"PLL_FAKE_UNCLEAR\x00" + b"\x00" * 64
```

- [ ] **Step 3: 写失败测试 tests/test_fake_vision_adapter.py**

```python
"""Tests for FakeVisionAdapter."""
from __future__ import annotations

import pytest

from tests.fixtures.images import (
    fake_face_bytes,
    fake_nsfw_bytes,
    fake_text_bytes,
    fake_unclear_bytes,
    safe_png_bytes,
)


@pytest.mark.asyncio
async def test_fake_returns_default_safe_objects_for_real_png():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(safe_png_bytes())

    assert result.is_safe is True
    assert result.reject_reasons == []
    assert result.scene_summary
    assert len(result.objects) >= 3
    for obj in result.objects:
        assert obj.label
        assert 0.0 <= obj.bbox.x <= 1.0
        assert 0.0 < obj.bbox.w <= 1.0


@pytest.mark.asyncio
async def test_fake_face_trigger_returns_unsafe():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(fake_face_bytes())
    assert result.is_safe is False
    assert "face_detected" in result.reject_reasons
    assert result.objects == []


@pytest.mark.asyncio
async def test_fake_nsfw_trigger_returns_unsafe():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(fake_nsfw_bytes())
    assert result.is_safe is False
    assert "nsfw" in result.reject_reasons


@pytest.mark.asyncio
async def test_fake_text_trigger_returns_unsafe():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(fake_text_bytes())
    assert result.is_safe is False
    assert "dominant_text" in result.reject_reasons


@pytest.mark.asyncio
async def test_fake_unclear_trigger_returns_unsafe():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(fake_unclear_bytes())
    assert result.is_safe is False
    assert "unclear_image" in result.reject_reasons


@pytest.mark.asyncio
async def test_fake_object_ids_are_unique():
    from app.adapters.vision.fake import FakeVisionAdapter

    result = await FakeVisionAdapter().analyze_image(safe_png_bytes())
    ids = [o.id for o in result.objects]
    assert len(ids) == len(set(ids))
```

- [ ] **Step 4: 跑测试确认失败**

```bash
uv run pytest tests/test_fake_vision_adapter.py -v
```

Expected: ImportError。

- [ ] **Step 5: 实现 app/adapters/__init__.py**

```python
"""AI provider adapters (vision / llm / tts / stt)."""
```

- [ ] **Step 6: 实现 app/adapters/vision/__init__.py**

```python
"""Vision adapters."""
```

- [ ] **Step 7: 实现 app/adapters/vision/base.py**

```python
"""VisionAdapter Protocol and shared types."""
from __future__ import annotations

from typing import Literal, Protocol

from app.schemas.vision import VisionResult

VisionIntent = Literal["safety_and_objects"]


class VisionAdapter(Protocol):
    """Provider-agnostic interface for image safety + object detection."""

    async def analyze_image(
        self,
        image_bytes: bytes,
        *,
        intent: VisionIntent = "safety_and_objects",
    ) -> VisionResult: ...
```

- [ ] **Step 8: 实现 app/adapters/vision/fake.py**

```python
"""FakeVisionAdapter: deterministic stub for tests + offline development."""
from __future__ import annotations

from app.adapters.vision.base import VisionIntent
from app.schemas.vision import BBox, DetectedObject, VisionResult

_TRIGGERS: dict[bytes, str] = {
    b"PLL_FAKE_FACE": "face_detected",
    b"PLL_FAKE_NSFW": "nsfw",
    b"PLL_FAKE_TEXT": "dominant_text",
    b"PLL_FAKE_UNCLEAR": "unclear_image",
    b"PLL_FAKE_VIOLENCE": "violence",
    b"PLL_FAKE_WEAPON": "weapons",
}

_DEFAULT_SAFE = VisionResult(
    is_safe=True,
    reject_reasons=[],
    scene_summary="A bright kitchen counter with baking ingredients arranged neatly.",
    objects=[
        DetectedObject(
            id="o_1",
            label="cupcake",
            bbox=BBox(x=0.42, y=0.55, w=0.18, h=0.22),
            confidence=0.92,
            persona_seed="sweet baker who loves sharing recipes",
        ),
        DetectedObject(
            id="o_2",
            label="saucepan",
            bbox=BBox(x=0.10, y=0.30, w=0.20, h=0.25),
            confidence=0.88,
            persona_seed="gruff old chef with decades of stories",
        ),
        DetectedObject(
            id="o_3",
            label="apple",
            bbox=BBox(x=0.68, y=0.40, w=0.12, h=0.16),
            confidence=0.81,
            persona_seed="cheerful and chatty about orchards",
        ),
    ],
)


class FakeVisionAdapter:
    async def analyze_image(
        self,
        image_bytes: bytes,
        *,
        intent: VisionIntent = "safety_and_objects",  # noqa: ARG002
    ) -> VisionResult:
        head = image_bytes[:32]
        for marker, reason in _TRIGGERS.items():
            if marker in head:
                return VisionResult(
                    is_safe=False,
                    reject_reasons=[reason],
                    scene_summary="",
                    objects=[],
                )
        return _DEFAULT_SAFE.model_copy(deep=True)
```

- [ ] **Step 9: 跑测试确认通过**

```bash
uv run pytest tests/test_fake_vision_adapter.py -v
```

Expected: 6 PASSED。

- [ ] **Step 10: Commit**

```bash
git add app/adapters/ tests/fixtures/ tests/test_fake_vision_adapter.py
git commit -m "feat(adapters): add VisionAdapter protocol and FakeVisionAdapter"
```

---

## Task 5: SafetyGuard 二次判定(TDD)

**Files:**
- Create: `app/services/__init__.py`、`app/services/safety_guard.py`
- Test: `tests/test_safety_guard.py`

**职责:** 在 VisionAdapter 给出结果后,做基于规则的二次判定:
1. 人脸:零容忍,但若 scene_summary 含 toy/cartoon/figurine 关键词,认为是误报玩偶,放行
2. 文本主体:objects 中标签为 "text" / "writing" / "document" 占比 ≥ 40% → 拒绝
3. 任意 reject_reason 都将是非安全的最终结论(模型的判断作为兜底)

- [ ] **Step 1: 写失败测试 tests/test_safety_guard.py**

```python
"""Tests for app.services.safety_guard.SafetyGuard."""
from __future__ import annotations

from app.schemas.vision import BBox, DetectedObject, VisionResult


def _safe_result_with(objects: list[DetectedObject], summary: str = "") -> VisionResult:
    return VisionResult(is_safe=True, reject_reasons=[], scene_summary=summary, objects=objects)


def _obj(label: str, *, x=0.1, y=0.1, w=0.1, h=0.1) -> DetectedObject:
    return DetectedObject(
        id=f"o_{label}",
        label=label,
        bbox=BBox(x=x, y=y, w=w, h=h),
        confidence=0.9,
        persona_seed=None,
    )


def test_passthrough_for_clean_safe_result():
    from app.services.safety_guard import SafetyGuard

    inp = _safe_result_with([_obj("cupcake")])
    out = SafetyGuard().review(inp)
    assert out.is_safe is True
    assert out.reject_reasons == []


def test_face_detected_is_zero_tolerance():
    from app.services.safety_guard import SafetyGuard

    inp = VisionResult(
        is_safe=False,
        reject_reasons=["face_detected"],
        scene_summary="A family photo at the beach.",
        objects=[],
    )
    out = SafetyGuard().review(inp)
    assert out.is_safe is False
    assert "face_detected" in out.reject_reasons


def test_face_on_toy_is_overridden_to_safe():
    from app.services.safety_guard import SafetyGuard

    inp = VisionResult(
        is_safe=False,
        reject_reasons=["face_detected"],
        scene_summary="A plush teddy bear toy on a kid's bed.",
        objects=[_obj("teddy_bear")],
    )
    out = SafetyGuard().review(inp)
    assert out.is_safe is True
    assert out.reject_reasons == []
    assert out.objects == inp.objects


def test_face_on_cartoon_is_overridden_to_safe():
    from app.services.safety_guard import SafetyGuard

    inp = VisionResult(
        is_safe=False,
        reject_reasons=["face_detected"],
        scene_summary="A cartoon poster of an animated character.",
        objects=[_obj("poster")],
    )
    out = SafetyGuard().review(inp)
    assert out.is_safe is True


def test_dominant_text_objects_rejected_even_if_model_says_safe():
    from app.services.safety_guard import SafetyGuard

    objects = [
        _obj("text", w=0.7, h=0.6),
        _obj("apple", w=0.05, h=0.05),
    ]
    inp = _safe_result_with(objects)
    out = SafetyGuard().review(inp)
    assert out.is_safe is False
    assert "dominant_text" in out.reject_reasons


def test_partial_text_within_scene_is_kept_safe():
    from app.services.safety_guard import SafetyGuard

    objects = [
        _obj("text", w=0.05, h=0.05),
        _obj("apple", w=0.4, h=0.4),
    ]
    inp = _safe_result_with(objects)
    out = SafetyGuard().review(inp)
    assert out.is_safe is True


def test_other_unsafe_reasons_passthrough():
    from app.services.safety_guard import SafetyGuard

    inp = VisionResult(
        is_safe=False,
        reject_reasons=["nsfw"],
        scene_summary="",
        objects=[],
    )
    out = SafetyGuard().review(inp)
    assert out.is_safe is False
    assert "nsfw" in out.reject_reasons
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_safety_guard.py -v
```

Expected: ImportError。

- [ ] **Step 3: 实现 app/services/__init__.py**

```python
"""Service layer (orchestration) modules."""
```

- [ ] **Step 4: 实现 app/services/safety_guard.py**

```python
"""Rule-based second pass on top of VisionAdapter output."""
from __future__ import annotations

from app.schemas.vision import VisionResult

_TOY_KEYWORDS = ("toy", "plush", "teddy", "doll", "figurine", "cartoon", "animated", "poster")
_TEXT_LABELS = {"text", "writing", "document", "handwriting", "sign"}


class SafetyGuard:
    """Apply additional content-safety rules on top of an adapter result."""

    def review(self, result: VisionResult) -> VisionResult:
        reasons = list(result.reject_reasons)
        is_safe = result.is_safe

        # Rule 1: face detection on toys/cartoons is a likely false positive.
        summary_lower = result.scene_summary.lower()
        if "face_detected" in reasons and any(kw in summary_lower for kw in _TOY_KEYWORDS):
            reasons = [r for r in reasons if r != "face_detected"]
            if not reasons:
                is_safe = True

        # Rule 2: text-dominant scenes (>=40% area) get rejected even if model said safe.
        text_area = sum(o.bbox.w * o.bbox.h for o in result.objects if o.label.lower() in _TEXT_LABELS)
        if text_area >= 0.40 and "dominant_text" not in reasons:
            reasons.append("dominant_text")
            is_safe = False

        return VisionResult(
            is_safe=is_safe,
            reject_reasons=reasons,
            scene_summary=result.scene_summary,
            objects=result.objects,
        )
```

- [ ] **Step 5: 跑测试确认通过**

```bash
uv run pytest tests/test_safety_guard.py -v
```

Expected: 7 PASSED。

- [ ] **Step 6: Commit**

```bash
git add app/services/__init__.py app/services/safety_guard.py tests/test_safety_guard.py
git commit -m "feat(services): add SafetyGuard rules for toy/cartoon override and text dominance"
```

---

## Task 6: VisionService 编排(TDD)

**Files:**
- Create: `app/services/vision_service.py`
- Test: `tests/test_vision_service.py`

**职责:** 接收 image_bytes,调 adapter,过 SafetyGuard,截断到最多 12 个 object,过滤掉 < 1.5% 占图比的小物体,返回最终 VisionResult。

- [ ] **Step 1: 写失败测试 tests/test_vision_service.py**

```python
"""Tests for app.services.vision_service.VisionService."""
from __future__ import annotations

import pytest

from app.schemas.vision import BBox, DetectedObject, VisionResult


class _StubAdapter:
    def __init__(self, result: VisionResult) -> None:
        self._result = result
        self.calls: list[bytes] = []

    async def analyze_image(self, image_bytes: bytes, *, intent: str = "safety_and_objects") -> VisionResult:
        self.calls.append(image_bytes)
        return self._result


def _obj(label: str, w: float, h: float, idx: int = 0) -> DetectedObject:
    return DetectedObject(
        id=f"o_{idx}",
        label=label,
        bbox=BBox(x=0.1, y=0.1, w=w, h=h),
        confidence=0.9,
        persona_seed=None,
    )


@pytest.mark.asyncio
async def test_passthrough_safe_result():
    from app.services.vision_service import VisionService

    adapter = _StubAdapter(
        VisionResult(
            is_safe=True,
            reject_reasons=[],
            scene_summary="kitchen",
            objects=[_obj("cupcake", 0.2, 0.2, idx=1)],
        )
    )
    svc = VisionService(adapter=adapter)
    out = await svc.analyze(b"\x00\x00")

    assert out.is_safe is True
    assert len(out.objects) == 1
    assert adapter.calls == [b"\x00\x00"]


@pytest.mark.asyncio
async def test_filters_small_objects_below_threshold():
    from app.services.vision_service import VisionService

    big = _obj("apple", 0.30, 0.20, idx=1)
    small = _obj("crumb", 0.05, 0.02, idx=2)  # area=0.001 < 0.015
    adapter = _StubAdapter(
        VisionResult(is_safe=True, scene_summary="", objects=[big, small])
    )
    out = await VisionService(adapter=adapter).analyze(b"x")

    labels = [o.label for o in out.objects]
    assert "apple" in labels
    assert "crumb" not in labels


@pytest.mark.asyncio
async def test_truncates_to_max_12_objects_keeping_largest():
    from app.services.vision_service import VisionService

    objects = [_obj(f"obj{i}", 0.10 + i * 0.01, 0.10, idx=i) for i in range(20)]
    adapter = _StubAdapter(
        VisionResult(is_safe=True, scene_summary="", objects=objects)
    )
    out = await VisionService(adapter=adapter).analyze(b"x")

    assert len(out.objects) == 12
    # 最大的 12 个被保留(area = w*h, h 固定 0.10,w 越大 area 越大)
    expected_labels = {f"obj{i}" for i in range(8, 20)}
    assert {o.label for o in out.objects} == expected_labels


@pytest.mark.asyncio
async def test_safety_guard_runs_before_returning():
    from app.services.vision_service import VisionService

    adapter = _StubAdapter(
        VisionResult(
            is_safe=False,
            reject_reasons=["face_detected"],
            scene_summary="cartoon character poster",
            objects=[_obj("poster", 0.3, 0.3, idx=1)],
        )
    )
    out = await VisionService(adapter=adapter).analyze(b"x")
    # SafetyGuard 把 cartoon 上的 face 误报清掉
    assert out.is_safe is True


@pytest.mark.asyncio
async def test_unsafe_result_clears_objects():
    from app.services.vision_service import VisionService

    adapter = _StubAdapter(
        VisionResult(
            is_safe=False,
            reject_reasons=["nsfw"],
            scene_summary="",
            objects=[_obj("anything", 0.3, 0.3, idx=1)],
        )
    )
    out = await VisionService(adapter=adapter).analyze(b"x")
    assert out.is_safe is False
    assert out.objects == []
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_vision_service.py -v
```

Expected: ImportError。

- [ ] **Step 3: 实现 app/services/vision_service.py**

```python
"""Vision orchestration: adapter → SafetyGuard → post-filter."""
from __future__ import annotations

from app.adapters.vision.base import VisionAdapter
from app.schemas.vision import VisionResult
from app.services.safety_guard import SafetyGuard

_MAX_OBJECTS = 12
_MIN_OBJECT_AREA = 0.015  # 1.5% of total image area


class VisionService:
    def __init__(
        self,
        *,
        adapter: VisionAdapter,
        safety_guard: SafetyGuard | None = None,
    ) -> None:
        self._adapter = adapter
        self._safety = safety_guard or SafetyGuard()

    async def analyze(self, image_bytes: bytes) -> VisionResult:
        raw = await self._adapter.analyze_image(image_bytes)
        reviewed = self._safety.review(raw)

        if not reviewed.is_safe:
            return VisionResult(
                is_safe=False,
                reject_reasons=list(reviewed.reject_reasons),
                scene_summary=reviewed.scene_summary,
                objects=[],
            )

        # 过滤过小 + 截断到 _MAX_OBJECTS,保留面积最大的 12 个
        kept = [o for o in reviewed.objects if (o.bbox.w * o.bbox.h) >= _MIN_OBJECT_AREA]
        kept.sort(key=lambda o: o.bbox.w * o.bbox.h, reverse=True)
        kept = kept[:_MAX_OBJECTS]

        return VisionResult(
            is_safe=True,
            reject_reasons=[],
            scene_summary=reviewed.scene_summary,
            objects=kept,
        )
```

- [ ] **Step 4: 跑测试确认通过**

```bash
uv run pytest tests/test_vision_service.py -v
```

Expected: 5 PASSED。

- [ ] **Step 5: Commit**

```bash
git add app/services/vision_service.py tests/test_vision_service.py
git commit -m "feat(services): add VisionService with size filtering and 12-cap"
```

---

## Task 7: 内存桶限流(TDD)

**Files:**
- Create: `app/utils/ratelimit.py`
- Test: `tests/test_ratelimit.py`

**职责:** 单实例内存级 sliding window 限流。每个 (key, endpoint) 维护一个 deque[float],超出 max 时返回 retry_after_s。

- [ ] **Step 1: 写失败测试 tests/test_ratelimit.py**

```python
"""Tests for app.utils.ratelimit.MemoryRateLimiter."""
from __future__ import annotations


def test_allows_within_quota():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=3, window_seconds=60.0)
    now = 1000.0
    for _ in range(3):
        ok, retry_after = rl.check("ip_1", now=now)
        assert ok is True
        assert retry_after == 0


def test_blocks_when_quota_exceeded():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=3, window_seconds=60.0)
    now = 1000.0
    for _ in range(3):
        rl.check("ip_1", now=now)
    ok, retry_after = rl.check("ip_1", now=now)
    assert ok is False
    assert 0 < retry_after <= 60


def test_quota_resets_after_window_slides():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=2, window_seconds=10.0)
    rl.check("ip_1", now=100.0)
    rl.check("ip_1", now=101.0)
    blocked, _ = rl.check("ip_1", now=105.0)
    assert blocked is False

    # 11 秒后,前两次落出窗口,应该再放行
    ok, _ = rl.check("ip_1", now=112.0)
    assert ok is True


def test_separate_keys_have_independent_quotas():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=1, window_seconds=60.0)
    a_ok, _ = rl.check("ip_a", now=100.0)
    b_ok, _ = rl.check("ip_b", now=100.0)
    assert a_ok is True
    assert b_ok is True

    a_blocked, _ = rl.check("ip_a", now=100.0)
    assert a_blocked is False


def test_retry_after_is_ceil_of_remaining_window():
    from app.utils.ratelimit import MemoryRateLimiter

    rl = MemoryRateLimiter(max_per_window=1, window_seconds=60.0)
    rl.check("ip_x", now=100.0)
    ok, retry_after = rl.check("ip_x", now=130.0)
    assert ok is False
    assert retry_after == 30  # 60 - (130 - 100)
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_ratelimit.py -v
```

Expected: ImportError。

- [ ] **Step 3: 实现 app/utils/ratelimit.py**

```python
"""Single-instance in-memory sliding window rate limiter."""
from __future__ import annotations

import math
import time
from collections import deque


class MemoryRateLimiter:
    """Per-key sliding window: at most `max_per_window` events in `window_seconds`."""

    def __init__(self, *, max_per_window: int, window_seconds: float) -> None:
        if max_per_window <= 0:
            raise ValueError("max_per_window must be > 0")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self._max = max_per_window
        self._window = window_seconds
        self._buckets: dict[str, deque[float]] = {}

    def check(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        """Returns (allowed, retry_after_s).

        retry_after_s = 0 when allowed; otherwise ceil seconds until oldest event drops out.
        Accepted requests are recorded; rejected ones are NOT.
        """
        ts = now if now is not None else time.monotonic()
        bucket = self._buckets.setdefault(key, deque())
        cutoff = ts - self._window

        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) < self._max:
            bucket.append(ts)
            return True, 0

        oldest = bucket[0]
        retry_after = math.ceil(self._window - (ts - oldest))
        return False, max(retry_after, 1)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
uv run pytest tests/test_ratelimit.py -v
```

Expected: 5 PASSED。

- [ ] **Step 5: Commit**

```bash
git add app/utils/ratelimit.py tests/test_ratelimit.py
git commit -m "feat(utils): add in-memory sliding window rate limiter"
```

---

## Task 8: vision_safety prompt 模板(TDD)

**Files:**
- Create: `app/prompts/__init__.py`、`app/prompts/vision_safety.py`
- Test: `tests/test_vision_prompt.py`

**职责:** 把"安全 + 物体识别"合一的 prompt 模板抽离成纯函数,返回 `list[ChatMessage]`,便于 OpenAI adapter 复用,也便于单测。

- [ ] **Step 1: 写失败测试 tests/test_vision_prompt.py**

```python
"""Tests for app.prompts.vision_safety."""
from __future__ import annotations


def test_build_messages_returns_system_and_user_pair():
    from app.prompts.vision_safety import build_vision_safety_messages

    messages = build_vision_safety_messages(image_data_url="data:image/jpeg;base64,abcd")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_system_message_lists_unsafe_categories():
    from app.prompts.vision_safety import build_vision_safety_messages

    sys_msg = build_vision_safety_messages(image_data_url="data:image/png;base64,xx")[0]
    text = sys_msg["content"] if isinstance(sys_msg["content"], str) else sys_msg["content"][0]["text"]
    for kw in ["face", "NSFW", "violence", "weapon", "text"]:
        assert kw.lower() in text.lower()


def test_user_message_embeds_image_url_part():
    from app.prompts.vision_safety import build_vision_safety_messages

    user_msg = build_vision_safety_messages(image_data_url="data:image/jpeg;base64,zz")[1]
    parts = user_msg["content"]
    assert isinstance(parts, list)
    image_parts = [p for p in parts if p.get("type") == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_max_objects_propagated_into_prompt():
    from app.prompts.vision_safety import build_vision_safety_messages

    sys_msg = build_vision_safety_messages(
        image_data_url="data:image/jpeg;base64,xx",
        max_objects=8,
    )[0]
    text = sys_msg["content"] if isinstance(sys_msg["content"], str) else sys_msg["content"][0]["text"]
    assert "8" in text


def test_response_schema_keys_documented_in_system_prompt():
    from app.prompts.vision_safety import build_vision_safety_messages

    sys_msg = build_vision_safety_messages(image_data_url="data:image/jpeg;base64,xx")[0]
    text = sys_msg["content"] if isinstance(sys_msg["content"], str) else sys_msg["content"][0]["text"]
    for key in ["is_safe", "reject_reasons", "scene_summary", "objects"]:
        assert key in text
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_vision_prompt.py -v
```

Expected: ImportError。

- [ ] **Step 3: 实现 app/prompts/__init__.py**

```python
"""Prompt templates."""
```

- [ ] **Step 4: 实现 app/prompts/vision_safety.py**

```python
"""Prompt template for combined safety check + object detection."""
from __future__ import annotations

from typing import Any

_SYSTEM_TEMPLATE = """You are an image analyzer for an English learning app.

STEP 1 — Safety check.
Mark the image UNSAFE if it contains any of:
- Identifiable human faces (real people, including children and group photos)
- NSFW content (nudity, sexual acts, suggestive imagery)
- Violence, blood
- Weapons of any kind
- Sensitive political symbols, flags, or propaganda
- Dominant text or handwriting (image is primarily text, occupying >40% area)
Allowed exceptions: cartoon characters, toys, plush figures, figurines.

STEP 2 — If safe, list up to {max_objects} distinct prominent OBJECTS that could
be playful conversation partners. Each object must:
- Be clearly visible and >= 1.5% of total image area
- Have an English label (lowercase, singular noun)
- Have a normalized bounding box [x, y, w, h] in [0, 1]
- Have a 1-line persona seed (short phrase describing potential character)

Output STRICT JSON, exactly this shape, no markdown fence, no commentary:
{{
  "is_safe": <bool>,
  "reject_reasons": [<reason_code>, ...],
  "scene_summary": "<1-2 sentence English description>",
  "objects": [
    {{
      "label": "<noun>",
      "bbox": [<x>, <y>, <w>, <h>],
      "persona_seed": "<short phrase>"
    }}
  ]
}}

Valid reject_reasons codes:
"face_detected" | "nsfw" | "violence" | "weapons" | "sensitive_symbols" | "dominant_text" | "unclear_image"
"""


def build_vision_safety_messages(
    *,
    image_data_url: str,
    max_objects: int = 12,
) -> list[dict[str, Any]]:
    """Return OpenAI chat-completions style messages for one-shot vision analysis."""
    system_text = _SYSTEM_TEMPLATE.format(max_objects=max_objects)
    return [
        {"role": "system", "content": system_text},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this image."},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        },
    ]
```

- [ ] **Step 5: 跑测试确认通过**

```bash
uv run pytest tests/test_vision_prompt.py -v
```

Expected: 5 PASSED。

- [ ] **Step 6: Commit**

```bash
git add app/prompts/ tests/test_vision_prompt.py
git commit -m "feat(prompts): add vision safety + object detection prompt builder"
```

---

## Task 9: POST /api/vision/analyze 端点(TDD,集成 with FakeAdapter)

**Files:**
- Create: `app/api/vision.py`
- Modify: `app/main.py`(挂 vision router + 注入 dependencies)
- Test: `tests/test_vision_endpoint.py`

**Why this comes before OpenAI adapter:** 端点正确性独立于厂商;先用 fake 跑通端到端逻辑(限流 / mime 校验 / 错误码),OpenAI 实现只需符合相同 Protocol。

**端点契约:**
- `POST /api/vision/analyze`,`multipart/form-data`,字段 `image`
- 200 → `VisionAnalyzeResponse`
- 422 → `{"code":"UNSAFE_IMAGE", "message":..., "details":{"reject_reasons":[...]}}`
- 413/415/429 → 对应错误码

- [ ] **Step 1: 写失败测试 tests/test_vision_endpoint.py**

```python
"""Integration tests for POST /api/vision/analyze using FakeVisionAdapter."""
from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.images import (
    fake_face_bytes,
    fake_nsfw_bytes,
    safe_png_bytes,
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_VISION_PER_MIN", "100")  # 防止测试相互限流
    from app.main import create_app

    return TestClient(create_app())


def _multipart(image_bytes: bytes, mime: str = "image/png", filename: str = "test.png"):
    return {"image": (filename, BytesIO(image_bytes), mime)}


def test_safe_image_returns_objects(client):
    resp = client.post("/api/vision/analyze", files=_multipart(safe_png_bytes()))
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_safe"] is True


    assert body["reject_reasons"] == []
    assert body["scene_summary"]
    assert len(body["objects"]) >= 1
    obj0 = body["objects"][0]
    assert {"id", "label", "bbox", "persona_seed"} <= set(obj0.keys())
    assert {"x", "y", "w", "h"} == set(obj0["bbox"].keys())


def test_safe_image_response_includes_request_id(client):
    resp = client.post(
        "/api/vision/analyze",
        files=_multipart(safe_png_bytes()),
        headers={"X-Request-ID": "req_test_xyz"},
    )
    assert resp.status_code == 200
    assert resp.json()["request_id"] == "req_test_xyz"
    assert resp.headers.get("x-request-id") == "req_test_xyz"


def test_face_image_returns_422_unsafe(client):
    resp = client.post("/api/vision/analyze", files=_multipart(fake_face_bytes()))
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "UNSAFE_IMAGE"
    assert "face_detected" in body["details"]["reject_reasons"]


def test_nsfw_image_returns_422_unsafe(client):
    resp = client.post("/api/vision/analyze", files=_multipart(fake_nsfw_bytes()))
    assert resp.status_code == 422
    assert "nsfw" in resp.json()["details"]["reject_reasons"]


def test_missing_image_field_returns_400(client):
    resp = client.post("/api/vision/analyze", data={})
    # FastAPI's own validation -> 422 from Pydantic on missing form field;
    # but our endpoint normalizes that to INVALID_INPUT 400 via dependency.
    assert resp.status_code in (400, 422)


def test_unsupported_mime_returns_415(client):
    resp = client.post(
        "/api/vision/analyze",
        files={"image": ("face.gif", BytesIO(b"GIF89a"), "image/gif")},
    )
    assert resp.status_code == 415
    assert resp.json()["code"] == "UNSUPPORTED_MEDIA"


def test_oversized_payload_returns_413(client, monkeypatch):
    monkeypatch.setenv("PLL_UPLOAD_MAX_BYTES", "1024")  # 1KB
    from app.main import create_app

    small_client = TestClient(create_app())
    resp = small_client.post(
        "/api/vision/analyze",
        files=_multipart(b"\x89PNG" + b"\x00" * 2048),  # >1KB
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_rate_limited_returns_429(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "fake")
    monkeypatch.setenv("PLL_RATE_LIMIT_VISION_PER_MIN", "2")
    from app.main import create_app

    c = TestClient(create_app())
    for _ in range(2):
        r = c.post("/api/vision/analyze", files=_multipart(safe_png_bytes()))
        assert r.status_code == 200
    r = c.post("/api/vision/analyze", files=_multipart(safe_png_bytes()))
    assert r.status_code == 429
    assert r.json()["code"] == "RATE_LIMITED"
    assert "retry-after" in {k.lower() for k in r.headers.keys()}
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_vision_endpoint.py -v
```

Expected: 多数 FAIL,因为路由不存在。

- [ ] **Step 3: 实现 app/api/vision.py**

```python
"""POST /api/vision/analyze endpoint."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.adapters.factory import build_vision_adapter
from app.config import Settings, get_settings
from app.errors import (
    InvalidInputError,
    PayloadTooLargeError,
    RateLimitedError,
    UnsafeImageError,
    UnsupportedMediaError,
)
from app.schemas.vision import VisionAnalyzeResponse
from app.services.vision_service import VisionService
from app.utils.ratelimit import MemoryRateLimiter

router = APIRouter(prefix="/api/vision", tags=["vision"])
log = structlog.get_logger("pll.vision")

# 单实例进程内的限流器。create_app() 启动时按 settings 重建。
_RATE_LIMITER: MemoryRateLimiter | None = None


def _ensure_limiter(settings: Settings) -> MemoryRateLimiter:
    global _RATE_LIMITER
    if _RATE_LIMITER is None:
        _RATE_LIMITER = MemoryRateLimiter(
            max_per_window=settings.rate_limit_vision_per_min,
            window_seconds=60.0,
        )
    return _RATE_LIMITER


def reset_rate_limiter() -> None:
    """For tests: drop the singleton between create_app() calls."""
    global _RATE_LIMITER
    _RATE_LIMITER = None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/analyze", response_model=VisionAnalyzeResponse)
async def analyze_image(
    request: Request,
    image: UploadFile = File(default=None),
    settings: Settings = Depends(get_settings),
) -> VisionAnalyzeResponse:
    if image is None or image.filename is None:
        raise InvalidInputError("missing required field 'image'")

    # MIME 校验
    mime = (image.content_type or "").lower()
    if mime not in settings.upload_allowed_mime:
        raise UnsupportedMediaError(mime or "<unknown>")

    # 限流
    limiter = _ensure_limiter(settings)
    ok, retry_after = limiter.check(_client_ip(request))
    if not ok:
        raise RateLimitedError(retry_after_s=retry_after)

    # 读取 + 大小校验
    image_bytes = await image.read()
    if len(image_bytes) > settings.upload_max_bytes:
        raise PayloadTooLargeError(
            f"file is {len(image_bytes)} bytes, max {settings.upload_max_bytes}"
        )

    # 调用业务
    adapter = build_vision_adapter(settings)
    service = VisionService(adapter=adapter)
    result = await service.analyze(image_bytes)

    if not result.is_safe:
        log.info("vision.unsafe", reasons=result.reject_reasons)
        raise UnsafeImageError(reasons=result.reject_reasons)

    request_id = request.headers.get("x-request-id", "req_unknown")
    log.info("vision.ok", objects=len(result.objects), request_id=request_id)

    return VisionAnalyzeResponse(
        request_id=request_id,
        is_safe=True,
        reject_reasons=[],
        scene_summary=result.scene_summary,
        objects=result.objects,
    )
```

> 注:`build_vision_adapter` 在 Task 11 实现。本 task 先创建一个最小占位让测试可跑——下一步先临时返回 FakeVisionAdapter,Task 11 替换为真正的工厂。

- [ ] **Step 4: 实现临时 app/adapters/factory.py(Task 11 会扩展)**

```python
"""Provider factory: pick vision adapter based on settings."""
from __future__ import annotations

from app.adapters.vision.base import VisionAdapter
from app.adapters.vision.fake import FakeVisionAdapter
from app.config import Settings


def build_vision_adapter(settings: Settings) -> VisionAdapter:
    if settings.ai_vision_provider == "fake":
        return FakeVisionAdapter()
    # OpenAI 分支留 Task 11
    raise NotImplementedError(f"vision provider not yet wired: {settings.ai_vision_provider}")
```

- [ ] **Step 5: 修改 app/main.py 挂 vision router 并重置限流器**

`create_app()` 在 `app.include_router(health.router)` 后追加:

```python
    from app.api import vision as vision_module

    vision_module.reset_rate_limiter()  # 新 app 实例 = 新限流器
    app.include_router(vision_module.router)
```

并把文件顶部 `from app.api import health` 改为:

```python
from app.api import health, vision  # noqa: F401  vision import is for side effects? No, used in create_app
```

实际上 Python 风格上把 `from app.api import vision as vision_module` 放在 `create_app()` 内部即可,避免顶层 import 副作用。删除顶层修改,只保留函数内的两行。

- [ ] **Step 6: 跑测试确认通过**

```bash
uv run pytest tests/test_vision_endpoint.py -v
```

Expected: 8 PASSED。

- [ ] **Step 7: 全量回归**

```bash
uv run pytest -v
```

Expected: 全部 PASSED。

- [ ] **Step 8: 手动启动验证**

```bash
uv run uvicorn app.main:app --reload --port 8000
```

另开终端构造一个真实小 PNG 测试。例如:

```bash
# 使用任何本地小图片
curl -F "image=@/path/to/some_image.png" http://127.0.0.1:8000/api/vision/analyze
```

Expected: 200,`{"request_id":"req_...","is_safe":true,"scene_summary":"A bright kitchen counter...","objects":[...]}`(因为是 fake adapter)。

按 Ctrl+C 停止。

- [ ] **Step 9: Commit**

```bash
git add app/api/vision.py app/adapters/factory.py app/main.py tests/test_vision_endpoint.py
git commit -m "feat(api): add POST /api/vision/analyze with rate-limit and MIME guard"
```

---

## Task 10: OpenAI VisionAdapter 实现(TDD,使用 respx mock httpx)

**Files:**
- Create: `app/adapters/vision/openai_vision.py`
- Test: `tests/test_openai_vision_adapter.py`

**实现要点:**
- 用 `httpx.AsyncClient` 直连 `{base_url}/chat/completions`
- request body 含 model + messages(由 `build_vision_safety_messages` 构造)+ `response_format={"type":"json_object"}`
- 解析 `choices[0].message.content` 为 JSON,映射到 `VisionResult`
- 失败映射:HTTP timeout → `UpstreamTimeoutError`;其余 4xx/5xx → `UpstreamFailureError`;JSON 解析失败 → `UpstreamFailureError`

- [ ] **Step 1: 写失败测试 tests/test_openai_vision_adapter.py**

```python
"""Tests for OpenAIVisionAdapter (httpx mocked via respx)."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError
from tests.fixtures.images import safe_png_bytes


def _build_response(json_payload: dict) -> dict:
    """Wrap a vision JSON object in the OpenAI chat-completions envelope."""
    return {
        "id": "chatcmpl-x",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(json_payload)},
                "finish_reason": "stop",
            }
        ],
    }


@pytest.mark.asyncio
@respx.mock
async def test_parses_safe_response_into_vision_result():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    payload = {
        "is_safe": True,
        "reject_reasons": [],
        "scene_summary": "A modern kitchen.",
        "objects": [
            {
                "label": "cupcake",
                "bbox": [0.4, 0.5, 0.2, 0.2],
                "persona_seed": "sweet baker",
            },
            {
                "label": "saucepan",
                "bbox": [0.1, 0.3, 0.2, 0.25],
                "persona_seed": "old chef",
            },
        ],
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_response(payload))
    )

    adapter = OpenAIVisionAdapter(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        timeout_s=10.0,
    )
    result = await adapter.analyze_image(safe_png_bytes())

    assert result.is_safe is True
    assert result.scene_summary == "A modern kitchen."
    assert len(result.objects) == 2
    assert result.objects[0].label == "cupcake"
    assert result.objects[0].bbox.x == 0.4


@pytest.mark.asyncio
@respx.mock
async def test_parses_unsafe_response():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    payload = {
        "is_safe": False,
        "reject_reasons": ["face_detected"],
        "scene_summary": "",
        "objects": [],
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_response(payload))
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    result = await adapter.analyze_image(safe_png_bytes())

    assert result.is_safe is False
    assert "face_detected" in result.reject_reasons


@pytest.mark.asyncio
@respx.mock
async def test_assigns_object_ids_when_provider_omits_them():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    payload = {
        "is_safe": True,
        "reject_reasons": [],
        "scene_summary": "scene",
        "objects": [
            {"label": "apple", "bbox": [0.1, 0.1, 0.1, 0.1], "persona_seed": "x"},
            {"label": "pear", "bbox": [0.2, 0.2, 0.1, 0.1], "persona_seed": "y"},
        ],
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_response(payload))
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    result = await adapter.analyze_image(safe_png_bytes())

    ids = [o.id for o in result.objects]
    assert len(set(ids)) == 2
    assert all(i for i in ids)  # 非空


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="server error")
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    with pytest.raises(UpstreamFailureError):
        await adapter.analyze_image(safe_png_bytes())


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        side_effect=httpx.TimeoutException("timed out")
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    with pytest.raises(UpstreamTimeoutError):
        await adapter.analyze_image(safe_png_bytes())


@pytest.mark.asyncio
@respx.mock
async def test_invalid_json_in_response_raises_upstream_failure():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    bad_envelope = {
        "choices": [{"message": {"content": "not-json-at-all"}, "finish_reason": "stop"}]
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=bad_envelope)
    )

    adapter = OpenAIVisionAdapter(api_key="sk-test", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    with pytest.raises(UpstreamFailureError):
        await adapter.analyze_image(safe_png_bytes())


@pytest.mark.asyncio
@respx.mock
async def test_request_includes_authorization_header_and_image_data_url():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        payload = {
            "is_safe": True,
            "reject_reasons": [],
            "scene_summary": "ok",
            "objects": [],
        }
        return httpx.Response(200, json=_build_response(payload))

    respx.post("https://api.openai.com/v1/chat/completions").mock(side_effect=_capture)

    adapter = OpenAIVisionAdapter(api_key="sk-secret", base_url="https://api.openai.com/v1", model="gpt-4o", timeout_s=10.0)
    await adapter.analyze_image(safe_png_bytes())

    assert captured["headers"].get("authorization") == "Bearer sk-secret"
    assert captured["body"]["model"] == "gpt-4o"
    user_msg = captured["body"]["messages"][1]
    image_part = next(p for p in user_msg["content"] if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/")
    assert "base64," in image_part["image_url"]["url"]
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_openai_vision_adapter.py -v
```

Expected: ImportError。

- [ ] **Step 3: 实现 app/adapters/vision/openai_vision.py**

```python
"""OpenAI Chat Completions adapter for vision (safety + objects)."""
from __future__ import annotations

import base64
import json

import httpx
import structlog

from app.adapters.vision.base import VisionIntent
from app.errors import UpstreamFailureError, UpstreamTimeoutError
from app.prompts.vision_safety import build_vision_safety_messages
from app.schemas.vision import BBox, DetectedObject, VisionResult

log = structlog.get_logger("pll.adapter.openai_vision")


def _detect_image_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"  # 兜底


def _to_data_url(image_bytes: bytes) -> str:
    mime = _detect_image_mime(image_bytes)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


class OpenAIVisionAdapter:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_s: float,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    async def analyze_image(
        self,
        image_bytes: bytes,
        *,
        intent: VisionIntent = "safety_and_objects",  # noqa: ARG002
    ) -> VisionResult:
        url = f"{self._base_url}/chat/completions"
        messages = build_vision_safety_messages(image_data_url=_to_data_url(image_bytes))
        body = {
            "model": self._model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("openai.vision.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.vision.http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("openai.vision.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider="openai",
                message=f"openai returned {resp.status_code}",
            )

        try:
            envelope = resp.json()
            content_str = envelope["choices"][0]["message"]["content"]
            payload = json.loads(content_str)
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("openai.vision.parse_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message="invalid JSON from upstream") from exc

        return _payload_to_result(payload)


def _payload_to_result(payload: dict) -> VisionResult:
    is_safe = bool(payload.get("is_safe", False))
    reasons = list(payload.get("reject_reasons") or [])
    summary = str(payload.get("scene_summary") or "")
    raw_objects = payload.get("objects") or []

    objects: list[DetectedObject] = []
    for idx, raw in enumerate(raw_objects, start=1):
        bbox_arr = raw.get("bbox") or [0, 0, 0, 0]
        if len(bbox_arr) != 4:
            continue
        try:
            confidence_raw = raw.get("confidence")
            if confidence_raw is None:
                confidence = 0.5
            else:
                confidence = max(0.0, min(1.0, float(confidence_raw)))
            objects.append(
                DetectedObject(
                    id=raw.get("id") or f"o_{idx}",
                    label=str(raw.get("label") or "object"),
                    bbox=BBox(
                        x=max(0.0, min(1.0, float(bbox_arr[0]))),
                        y=max(0.0, min(1.0, float(bbox_arr[1]))),
                        w=max(0.0, min(1.0, float(bbox_arr[2]))),
                        h=max(0.0, min(1.0, float(bbox_arr[3]))),
                    ),
                    confidence=confidence,
                    persona_seed=raw.get("persona_seed"),
                )
            )
        except (ValueError, TypeError):
            continue

    return VisionResult(
        is_safe=is_safe,
        reject_reasons=reasons,
        scene_summary=summary,
        objects=objects,
    )
```

- [ ] **Step 4: 跑测试确认通过**

```bash
uv run pytest tests/test_openai_vision_adapter.py -v
```

Expected: 7 PASSED。

- [ ] **Step 5: Commit**

```bash
git add app/adapters/vision/openai_vision.py tests/test_openai_vision_adapter.py
git commit -m "feat(adapters): add OpenAIVisionAdapter using httpx with respx-tested error mapping"
```

---

## Task 11: Adapter factory wiring(TDD)

**Files:**
- Modify: `app/adapters/factory.py`(实现 openai 分支)
- Test: `tests/test_vision_factory.py`

- [ ] **Step 1: 写失败测试 tests/test_vision_factory.py**

```python
"""Tests for app.adapters.factory.build_vision_adapter."""
from __future__ import annotations


def test_factory_returns_fake_when_provider_is_fake(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "fake")
    from app.adapters.factory import build_vision_adapter
    from app.adapters.vision.fake import FakeVisionAdapter
    from app.config import Settings

    adapter = build_vision_adapter(Settings())
    assert isinstance(adapter, FakeVisionAdapter)


def test_factory_returns_openai_adapter_when_configured(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "openai")
    monkeypatch.setenv("PLL_OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("PLL_OPENAI_MODEL_VISION", "gpt-4o")

    from app.adapters.factory import build_vision_adapter
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter
    from app.config import Settings

    adapter = build_vision_adapter(Settings())
    assert isinstance(adapter, OpenAIVisionAdapter)
    # 内部字段被正确传入
    assert adapter._api_key == "sk-test"  # noqa: SLF001
    assert adapter._model == "gpt-4o"  # noqa: SLF001
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_vision_factory.py -v
```

Expected: 第二个测试 FAIL(NotImplementedError)。

- [ ] **Step 3: 完整替换 app/adapters/factory.py**

```python
"""Provider factory: pick vision adapter based on settings."""
from __future__ import annotations

from app.adapters.vision.base import VisionAdapter
from app.adapters.vision.fake import FakeVisionAdapter
from app.adapters.vision.openai_vision import OpenAIVisionAdapter
from app.config import Settings


def build_vision_adapter(settings: Settings) -> VisionAdapter:
    if settings.ai_vision_provider == "fake":
        return FakeVisionAdapter()
    if settings.ai_vision_provider == "openai":
        if settings.openai_api_key is None:
            # 应该已被 Settings.model_validator 拦下,但保险起见再校验
            raise RuntimeError("openai provider selected but PLL_OPENAI_API_KEY is missing")
        return OpenAIVisionAdapter(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            model=settings.openai_model_vision,
            timeout_s=settings.openai_request_timeout_s,
        )
    raise RuntimeError(f"unknown vision provider: {settings.ai_vision_provider}")
```

- [ ] **Step 4: 跑测试确认通过**

```bash
uv run pytest tests/test_vision_factory.py -v
```

Expected: 2 PASSED。

- [ ] **Step 5: 全量后端回归 + lint**

```bash
uv run pytest -v
uv run ruff check app tests
```

Expected: 全绿。如有 lint 错误,`uv run ruff check --fix app tests` 自动修复后再跑。

- [ ] **Step 6: Commit**

```bash
git add app/adapters/factory.py tests/test_vision_factory.py
git commit -m "feat(adapters): wire factory to dispatch openai provider"
```

---

## Task 12: 前端 - 客户端预检 utility

预检在用户触发上传那一刻就拦掉明显违规(MIME 不对/超 8MB),避免无意义的网络往返。后续真正的"内容安全"判定仍交给后端 SafetyGuard。

**Files:**
- Create: `frontend/src/lib/safety/preUpload.ts`
- Create: `frontend/src/lib/safety/preUpload.test.ts`

- [ ] **Step 1: 写失败的单元测试**

`frontend/src/lib/safety/preUpload.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { preCheckFile, MAX_UPLOAD_BYTES, ALLOWED_MIME } from './preUpload';

function makeFile(name: string, type: string, size: number): File {
  const buf = new Uint8Array(size);
  return new File([buf], name, { type });
}

describe('preCheckFile', () => {
  it('接受 image/jpeg 8MB 以内', () => {
    const f = makeFile('a.jpg', 'image/jpeg', 1024 * 1024);
    const r = preCheckFile(f);
    expect(r.ok).toBe(true);
  });

  it('接受 image/png/webp', () => {
    for (const t of ['image/png', 'image/webp']) {
      const r = preCheckFile(makeFile('a', t, 100));
      expect(r.ok).toBe(true);
    }
  });

  it('拒绝 image/heic 与 application/pdf', () => {
    for (const t of ['image/heic', 'application/pdf']) {
      const r = preCheckFile(makeFile('a', t, 100));
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.code).toBe('UNSUPPORTED');
    }
  });

  it('拒绝超过 8MB', () => {
    const f = makeFile('big.jpg', 'image/jpeg', MAX_UPLOAD_BYTES + 1);
    const r = preCheckFile(f);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.code).toBe('PAYLOAD_TOO_LARGE');
  });

  it('暴露白名单常量,便于 UI 提示', () => {
    expect(ALLOWED_MIME).toContain('image/jpeg');
    expect(MAX_UPLOAD_BYTES).toBe(8 * 1024 * 1024);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/lib/safety/preUpload.test.ts
```

Expected: 模块解析失败,5 项全部 FAILED。

- [ ] **Step 3: 写最小实现**

`frontend/src/lib/safety/preUpload.ts`:

```typescript
export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
export const ALLOWED_MIME = ['image/jpeg', 'image/png', 'image/webp'] as const;

export type PreCheckResult =
  | { ok: true }
  | { ok: false; code: 'UNSUPPORTED' | 'PAYLOAD_TOO_LARGE'; message: string };

export function preCheckFile(file: File): PreCheckResult {
  if (!ALLOWED_MIME.includes(file.type as (typeof ALLOWED_MIME)[number])) {
    return {
      ok: false,
      code: 'UNSUPPORTED',
      message: `仅支持 JPEG / PNG / WebP,你给的是 ${file.type || '未知类型'}。`,
    };
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return {
      ok: false,
      code: 'PAYLOAD_TOO_LARGE',
      message: `图片不能大于 ${(MAX_UPLOAD_BYTES / 1024 / 1024).toFixed(0)}MB。`,
    };
  }
  return { ok: true };
}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd frontend && npm test -- --run src/lib/safety/preUpload.test.ts
```

Expected: 5 PASSED。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/safety/preUpload.ts frontend/src/lib/safety/preUpload.test.ts
git commit -m "feat(frontend): add client-side pre-upload mime/size guard"
```

---

## Task 13: 前端 - 图片压缩 utility

经过预检的图片仍可能很大(8MB JPEG)。压到"最长边 ≤1600px、JPEG quality≈0.82"足够 Vision 识别,又能显著降低上行带宽与延迟。

**Files:**
- Create: `frontend/src/lib/image/compress.ts`
- Create: `frontend/src/lib/image/compress.test.ts`

- [ ] **Step 1: 写失败的单元测试**

`frontend/src/lib/image/compress.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { compressIfNeeded } from './compress';

class FakeImage {
  width = 0;
  height = 0;
  src = '';
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor() {
    (globalThis as unknown as { __lastImage?: FakeImage }).__lastImage = this;
    queueMicrotask(() => {
      this.width = 4000;
      this.height = 3000;
      this.onload?.();
    });
  }
}

beforeEach(() => {
  (globalThis as unknown as { Image: typeof FakeImage }).Image = FakeImage;
});

function fakeCanvasReturning(blob: Blob | null) {
  const ctx = { drawImage: vi.fn() };
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => ctx,
    toBlob: (cb: (b: Blob | null) => void) => cb(blob),
  };
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
    if (tag === 'canvas') return canvas as unknown as HTMLCanvasElement;
    return document.createElementNS('http://www.w3.org/1999/xhtml', tag) as HTMLElement;
  });
  return canvas;
}

function makeFile(name: string, type: string, size: number): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe('compressIfNeeded', () => {
  it('小于阈值且最长边足够小,直接返回原文件', async () => {
    const original = makeFile('a.jpg', 'image/jpeg', 100 * 1024);
    const out = await compressIfNeeded(original, { maxEdge: 1600, sizeThresholdBytes: 1_500_000 });
    expect(out).toBe(original);
  });

  it('超过 sizeThreshold 时尝试压缩,产物为 image/jpeg', async () => {
    const original = makeFile('big.jpg', 'image/jpeg', 5 * 1024 * 1024);
    const compressedBlob = new Blob([new Uint8Array(800 * 1024)], { type: 'image/jpeg' });
    fakeCanvasReturning(compressedBlob);

    const out = await compressIfNeeded(original, {
      maxEdge: 1600,
      sizeThresholdBytes: 1_500_000,
    });

    expect(out.type).toBe('image/jpeg');
    expect(out.size).toBeLessThan(original.size);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/lib/image/compress.test.ts
```

Expected: 模块未找到,2 项 FAILED。

- [ ] **Step 3: 写最小实现**

`frontend/src/lib/image/compress.ts`:

```typescript
export interface CompressOptions {
  maxEdge: number;
  sizeThresholdBytes: number;
  quality?: number;
}

const DEFAULTS: Required<CompressOptions> = {
  maxEdge: 1600,
  sizeThresholdBytes: 1_500_000,
  quality: 0.82,
};

export async function compressIfNeeded(
  file: File,
  opts: Partial<CompressOptions> = {},
): Promise<File> {
  const cfg = { ...DEFAULTS, ...opts };

  if (file.size <= cfg.sizeThresholdBytes) return file;

  const dataUrl = await readAsDataURL(file);
  const img = await loadImage(dataUrl);

  const longest = Math.max(img.width, img.height);
  const scale = longest > cfg.maxEdge ? cfg.maxEdge / longest : 1;
  const w = Math.round(img.width * scale);
  const h = Math.round(img.height * scale);

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  if (!ctx) return file;
  ctx.drawImage(img, 0, 0, w, h);

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, 'image/jpeg', cfg.quality),
  );
  if (!blob || blob.size >= file.size) return file;

  const newName = file.name.replace(/\.(png|webp|jpe?g)$/i, '') + '.jpg';
  return new File([blob], newName, { type: 'image/jpeg' });
}

function readAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(reader.error ?? new Error('read failed'));
    reader.readAsDataURL(file);
  });
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('image decode failed'));
    img.src = src;
  });
}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd frontend && npm test -- --run src/lib/image/compress.test.ts
```

Expected: 2 PASSED。

> 备注:这一层在 jsdom 下只能验证"分支与产物类型",真实像素压缩效果会在 Task 19 的浏览器手动验证里覆盖。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/image/compress.ts frontend/src/lib/image/compress.test.ts
git commit -m "feat(frontend): add canvas-based image downscale utility"
```

---

## Task 14: 前端 - api.ts 扩展 analyzeImage

把"调用后端 /api/vision/analyze"封装成单一函数,统一处理 multipart 构造与错误码翻译,方便组件层只关心成功路径。

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/api.test.ts`

- [ ] **Step 1: 写失败的测试**

`frontend/src/lib/api.test.ts`:

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { analyzeImage, ApiError } from './api';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
});

function jsonResponse(body: unknown, init: ResponseInit = { status: 200 }) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

describe('analyzeImage', () => {
  it('成功时返回 VisionAnalyzeResponse', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        request_id: 'req-1',
        is_safe: true,
        reject_reasons: [],
        scene_summary: 'kitchen',
        objects: [
          {
            id: 'obj_1',
            label: 'cup',
            bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 },
            confidence: 0.9,
          },
        ],
      }),
    );

    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    const out = await analyzeImage(file);
    expect(out.objects).toHaveLength(1);
    expect(out.objects[0].label).toBe('cup');

    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe('/api/vision/analyze');
    expect((call[1] as RequestInit).method).toBe('POST');
  });

  it('UNSAFE_IMAGE 时抛 ApiError 携带 code', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          code: 'UNSAFE_IMAGE',
          message: '这张图不能用于学习。',
          details: { reject_reasons: ['face_detected'] },
        },
        { status: 422 },
      ),
    );
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    await expect(analyzeImage(file)).rejects.toMatchObject({
      code: 'UNSAFE_IMAGE',
      status: 422,
    });
  });

  it('429 时把 retry-after 透传到 ApiError', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          code: 'RATE_LIMITED',
          message: 'slow down',
          details: { retry_after_s: 7 },
        },
        { status: 429, headers: { 'Retry-After': '7' } },
      ),
    );
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    try {
      await analyzeImage(file);
      throw new Error('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).code).toBe('RATE_LIMITED');
      expect((e as ApiError).retryAfter).toBe(7);
    }
  });

  it('网络异常时抛 ApiError code=NETWORK', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    await expect(analyzeImage(file)).rejects.toMatchObject({ code: 'NETWORK' });
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/lib/api.test.ts
```

Expected: `analyzeImage / ApiError` 未导出,4 项 FAILED。

- [ ] **Step 3: 修改 `frontend/src/lib/api.ts`,在现有 health 函数旁追加**

`frontend/src/lib/api.ts`(完整文件):

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

export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DetectedObject {
  id: string;
  label: string;
  bbox: BBox;
  confidence: number;
  persona_seed?: string | null;
}

export interface VisionAnalyzeResponse {
  request_id: string;
  is_safe: boolean;
  reject_reasons: string[];
  scene_summary: string;
  objects: DetectedObject[];
}

export type ApiErrorCode =
  | 'INVALID_INPUT'
  | 'PAYLOAD_TOO_LARGE'
  | 'UNSUPPORTED_MEDIA'
  | 'UNSAFE_IMAGE'
  | 'RATE_LIMITED'
  | 'UPSTREAM_FAILURE'
  | 'UPSTREAM_TIMEOUT'
  | 'NETWORK'
  | 'UNKNOWN';

export class ApiError extends Error {
  code: ApiErrorCode;
  status: number;
  retryAfter?: number;
  rejectReasons?: string[];

  constructor(opts: {
    code: ApiErrorCode;
    message: string;
    status: number;
    retryAfter?: number;
    rejectReasons?: string[];
  }) {
    super(opts.message);
    this.code = opts.code;
    this.status = opts.status;
    this.retryAfter = opts.retryAfter;
    this.rejectReasons = opts.rejectReasons;
  }
}

export async function analyzeImage(file: File): Promise<VisionAnalyzeResponse> {
  const fd = new FormData();
  fd.append('image', file);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/vision/analyze`, { method: 'POST', body: fd });
  } catch {
    throw new ApiError({ code: 'NETWORK', message: '网络异常,请稍后重试。', status: 0 });
  }

  if (res.ok) {
    return (await res.json()) as VisionAnalyzeResponse;
  }

  let body: {
    code?: ApiErrorCode;
    message?: string;
    details?: { retry_after_s?: number; reject_reasons?: string[] };
  } = {};
  try {
    body = await res.json();
  } catch {
    /* ignore: 非 JSON 体走默认 */
  }

  const headerRetry = Number(res.headers.get('Retry-After'));
  const retryAfter =
    body.details?.retry_after_s ?? (Number.isFinite(headerRetry) && headerRetry > 0 ? headerRetry : undefined);

  throw new ApiError({
    code: body.code ?? 'UNKNOWN',
    message: body.message ?? `请求失败:${res.status}`,
    status: res.status,
    retryAfter,
    rejectReasons: body.details?.reject_reasons,
  });
}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd frontend && npm test -- --run src/lib/api.test.ts
```

Expected: 4 PASSED。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/api.test.ts
git commit -m "feat(frontend): add analyzeImage api wrapper with typed errors"
```

---

## Task 15: 前端 - UploadZone 组件

UploadZone 负责"接收用户给的文件"——同时支持拖拽和点击选文件——并把通过预检的文件冒泡给父组件,违规时就地展示提示。

**Files:**
- Create: `frontend/src/components/UploadZone.tsx`
- Create: `frontend/src/components/UploadZone.test.tsx`

- [ ] **Step 1: 写失败的测试**

`frontend/src/components/UploadZone.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import UploadZone from './UploadZone';

function makeFile(name: string, type: string, size = 100): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe('UploadZone', () => {
  it('点击 input 选合法 jpeg 时回调 onFile', () => {
    const onFile = vi.fn();
    render(<UploadZone onFile={onFile} />);
    const input = screen.getByTestId('upload-input') as HTMLInputElement;

    const file = makeFile('a.jpg', 'image/jpeg');
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFile).toHaveBeenCalledWith(file);
  });

  it('drop 不支持的类型时显示错误,且不触发 onFile', () => {
    const onFile = vi.fn();
    render(<UploadZone onFile={onFile} />);
    const dropTarget = screen.getByTestId('upload-zone');

    const file = makeFile('a.heic', 'image/heic');
    fireEvent.drop(dropTarget, { dataTransfer: { files: [file] } });

    expect(onFile).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/仅支持/);
  });

  it('dragOver 时切换 high-light 样式', () => {
    render(<UploadZone onFile={() => {}} />);
    const dropTarget = screen.getByTestId('upload-zone');
    fireEvent.dragOver(dropTarget);
    expect(dropTarget.className).toMatch(/border-sky-500|bg-sky-50/);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/components/UploadZone.test.tsx
```

Expected: 模块未导出,3 项 FAILED。

- [ ] **Step 3: 写最小实现**

`frontend/src/components/UploadZone.tsx`:

```tsx
import { useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { preCheckFile } from '../lib/safety/preUpload';

interface Props {
  onFile: (file: File) => void;
}

export default function UploadZone({ onFile }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [hover, setHover] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function accept(file: File | undefined) {
    if (!file) return;
    setError(null);
    const r = preCheckFile(file);
    if (!r.ok) {
      setError(r.message);
      return;
    }
    onFile(file);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    accept(e.target.files?.[0]);
    e.target.value = '';
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setHover(false);
    accept(e.dataTransfer.files?.[0]);
  }

  function onDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setHover(true);
  }

  function onDragLeave() {
    setHover(false);
  }

  const base =
    'flex flex-col items-center justify-center gap-3 w-full max-w-xl mx-auto rounded-2xl border-2 border-dashed p-10 cursor-pointer transition-colors';
  const tone = hover ? 'border-sky-500 bg-sky-50' : 'border-slate-300 bg-white hover:bg-slate-50';

  return (
    <div className="w-full">
      <div
        data-testid="upload-zone"
        className={`${base} ${tone}`}
        onClick={() => inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
        }}
      >
        <p className="text-lg font-medium text-slate-800">把图片拖到这里,或点击选择文件</p>
        <p className="text-sm text-slate-500">支持 JPEG / PNG / WebP,单张 ≤ 8MB</p>
        <input
          ref={inputRef}
          data-testid="upload-input"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={onChange}
        />
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm text-rose-600 text-center">
          {error}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd frontend && npm test -- --run src/components/UploadZone.test.tsx
```

Expected: 3 PASSED。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/UploadZone.tsx frontend/src/components/UploadZone.test.tsx
git commit -m "feat(frontend): add UploadZone with drag-drop and file picker"
```

---

## Task 16: 前端 - ImageCanvas 组件

ImageCanvas 把已选图片以"保持纵横比、最大宽度受限"的方式渲染出来,并对外暴露一个 ref 以便 HotspotOverlay 拿到真实显示尺寸做坐标换算。

**Files:**
- Create: `frontend/src/components/ImageCanvas.tsx`
- Create: `frontend/src/components/ImageCanvas.test.tsx`

- [ ] **Step 1: 写失败的测试**

`frontend/src/components/ImageCanvas.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ImageCanvas from './ImageCanvas';

describe('ImageCanvas', () => {
  it('为传入的 file 渲染 <img> 并设置 alt', () => {
    const created: string[] = [];
    const origCreate = URL.createObjectURL;
    URL.createObjectURL = vi.fn((blob: Blob) => {
      const url = `blob:fake-${created.length}`;
      created.push(url);
      void blob;
      return url;
    }) as typeof URL.createObjectURL;
    URL.revokeObjectURL = vi.fn();

    const file = new File([new Uint8Array(10)], 'pic.jpg', { type: 'image/jpeg' });
    render(<ImageCanvas file={file} alt="用户上传的图片" />);
    const img = screen.getByRole('img') as HTMLImageElement;
    expect(img.src.startsWith('blob:')).toBe(true);
    expect(img.alt).toBe('用户上传的图片');

    URL.createObjectURL = origCreate;
  });

  it('onLoad 时通过 onReady 回调汇报渲染尺寸', () => {
    const onReady = vi.fn();
    URL.createObjectURL = vi.fn(() => 'blob:fake') as typeof URL.createObjectURL;
    URL.revokeObjectURL = vi.fn();

    const file = new File([new Uint8Array(10)], 'pic.jpg', { type: 'image/jpeg' });
    render(<ImageCanvas file={file} alt="x" onReady={onReady} />);
    const img = screen.getByRole('img') as HTMLImageElement;

    Object.defineProperty(img, 'naturalWidth', { value: 1200, configurable: true });
    Object.defineProperty(img, 'naturalHeight', { value: 800, configurable: true });
    Object.defineProperty(img, 'clientWidth', { value: 600, configurable: true });
    Object.defineProperty(img, 'clientHeight', { value: 400, configurable: true });

    img.dispatchEvent(new Event('load'));
    expect(onReady).toHaveBeenCalledWith({
      naturalWidth: 1200,
      naturalHeight: 800,
      renderedWidth: 600,
      renderedHeight: 400,
    });
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/components/ImageCanvas.test.tsx
```

Expected: 2 项 FAILED(模块未导出)。

- [ ] **Step 3: 写最小实现**

`frontend/src/components/ImageCanvas.tsx`:

```tsx
import { useEffect, useRef, useState, type SyntheticEvent } from 'react';

export interface ImageReadyInfo {
  naturalWidth: number;
  naturalHeight: number;
  renderedWidth: number;
  renderedHeight: number;
}

interface Props {
  file: File;
  alt: string;
  onReady?: (info: ImageReadyInfo) => void;
}

export default function ImageCanvas({ file, alt, onReady }: Props) {
  const [src, setSrc] = useState<string>('');
  const imgRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setSrc(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handleLoad(_e: SyntheticEvent<HTMLImageElement>) {
    const img = imgRef.current;
    if (!img || !onReady) return;
    onReady({
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      renderedWidth: img.clientWidth,
      renderedHeight: img.clientHeight,
    });
  }

  if (!src) return null;
  return (
    <img
      ref={imgRef}
      src={src}
      alt={alt}
      onLoad={handleLoad}
      className="block max-w-full h-auto rounded-xl shadow"
    />
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd frontend && npm test -- --run src/components/ImageCanvas.test.tsx
```

Expected: 2 PASSED。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ImageCanvas.tsx frontend/src/components/ImageCanvas.test.tsx
git commit -m "feat(frontend): add ImageCanvas with onReady size reporting"
```

---

## Task 17: 前端 - HotspotOverlay 组件

HotspotOverlay 在已渲染的图片上叠一层 SVG,根据归一化 bbox 画出可点击的方框,hover 时显示 label,点击时把对应 DetectedObject 抛给父组件。

**Files:**
- Create: `frontend/src/components/HotspotOverlay.tsx`
- Create: `frontend/src/components/HotspotOverlay.test.tsx`

- [ ] **Step 1: 写失败的测试**

`frontend/src/components/HotspotOverlay.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HotspotOverlay from './HotspotOverlay';
import type { DetectedObject } from '../lib/api';

const objects: DetectedObject[] = [
  { id: 'obj_1', label: 'cup', bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 }, confidence: 0.9 },
  { id: 'obj_2', label: 'lamp', bbox: { x: 0.5, y: 0.5, w: 0.1, h: 0.1 }, confidence: 0.8 },
];

describe('HotspotOverlay', () => {
  it('渲染与对象数量匹配的 hotspot 元素', () => {
    render(
      <HotspotOverlay
        renderedWidth={400}
        renderedHeight={300}
        objects={objects}
        onSelect={() => {}}
      />,
    );
    expect(screen.getAllByRole('button', { name: /cup|lamp/ })).toHaveLength(2);
  });

  it('点击 hotspot 触发 onSelect 并传入对应对象', () => {
    const onSelect = vi.fn();
    render(
      <HotspotOverlay
        renderedWidth={400}
        renderedHeight={300}
        objects={objects}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /cup/ }));
    expect(onSelect).toHaveBeenCalledWith(objects[0]);
  });

  it('SVG viewBox 与 renderedWidth/Height 一致', () => {
    const { container } = render(
      <HotspotOverlay
        renderedWidth={500}
        renderedHeight={250}
        objects={objects}
        onSelect={() => {}}
      />,
    );
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('viewBox')).toBe('0 0 500 250');
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/components/HotspotOverlay.test.tsx
```

Expected: 3 项 FAILED(模块未导出)。

- [ ] **Step 3: 写最小实现**

`frontend/src/components/HotspotOverlay.tsx`:

```tsx
import type { DetectedObject } from '../lib/api';

interface Props {
  renderedWidth: number;
  renderedHeight: number;
  objects: DetectedObject[];
  onSelect: (obj: DetectedObject) => void;
}

export default function HotspotOverlay({
  renderedWidth,
  renderedHeight,
  objects,
  onSelect,
}: Props) {
  if (renderedWidth <= 0 || renderedHeight <= 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={renderedWidth}
      height={renderedHeight}
      viewBox={`0 0 ${renderedWidth} ${renderedHeight}`}
    >
      {objects.map((obj) => {
        const x = obj.bbox.x * renderedWidth;
        const y = obj.bbox.y * renderedHeight;
        const w = obj.bbox.w * renderedWidth;
        const h = obj.bbox.h * renderedHeight;
        return (
          <g key={obj.id} className="pointer-events-auto">
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill="rgba(56,189,248,0.12)"
              stroke="rgb(2,132,199)"
              strokeWidth={2}
              rx={6}
              role="button"
              aria-label={obj.label}
              tabIndex={0}
              style={{ cursor: 'pointer' }}
              onClick={() => onSelect(obj)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onSelect(obj);
              }}
            />
            <text
              x={x + 6}
              y={y + 18}
              fill="rgb(15,23,42)"
              style={{
                font: '600 12px ui-sans-serif, system-ui, sans-serif',
                paintOrder: 'stroke',
                stroke: 'white',
                strokeWidth: 3,
              }}
              pointerEvents="none"
            >
              {obj.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd frontend && npm test -- --run src/components/HotspotOverlay.test.tsx
```

Expected: 3 PASSED。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/HotspotOverlay.tsx frontend/src/components/HotspotOverlay.test.tsx
git commit -m "feat(frontend): add HotspotOverlay with svg bbox interactions"
```

---

## Task 18: 前端 - PersonaPlaceholderPanel + 页面装配

把 UploadZone / ImageCanvas / HotspotOverlay 在一个 StudioPage 里串起来,给 Phase 2 提供"上传 → 看图 → 看热点 → 点击弹占位面板"的端到端体验。HomePage 仍保留欢迎语,App.tsx 用极简哈希路由切换。

**Files:**
- Create: `frontend/src/components/PersonaPlaceholderPanel.tsx`
- Create: `frontend/src/components/PersonaPlaceholderPanel.test.tsx`
- Create: `frontend/src/pages/HomePage.tsx`
- Create: `frontend/src/pages/StudioPage.tsx`
- Create: `frontend/src/pages/StudioPage.test.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 写 PersonaPlaceholderPanel 失败的测试**

`frontend/src/components/PersonaPlaceholderPanel.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PersonaPlaceholderPanel from './PersonaPlaceholderPanel';
import type { DetectedObject } from '../lib/api';

const obj: DetectedObject = {
  id: 'obj_1',
  label: 'cup',
  bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 },
  confidence: 0.9,
};

describe('PersonaPlaceholderPanel', () => {
  it('展示标签并提示后续阶段会接入对话', () => {
    render(<PersonaPlaceholderPanel object={obj} onClose={() => {}} />);
    expect(screen.getByText(/cup/)).toBeInTheDocument();
    expect(screen.getByText(/Phase 3/)).toBeInTheDocument();
  });

  it('点击关闭按钮回调 onClose', () => {
    const onClose = vi.fn();
    render(<PersonaPlaceholderPanel object={obj} onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /关闭|close/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/components/PersonaPlaceholderPanel.test.tsx
```

Expected: 2 项 FAILED。

- [ ] **Step 3: 写 PersonaPlaceholderPanel 实现**

`frontend/src/components/PersonaPlaceholderPanel.tsx`:

```tsx
import type { DetectedObject } from '../lib/api';

interface Props {
  object: DetectedObject;
  onClose: () => void;
}

export default function PersonaPlaceholderPanel({ object, onClose }: Props) {
  return (
    <aside
      role="dialog"
      aria-label={`${object.label} 的占位面板`}
      className="fixed right-4 top-4 z-30 w-80 rounded-2xl border border-slate-200 bg-white p-5 shadow-xl"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500">已识别</p>
          <h2 className="text-lg font-semibold text-slate-900">{object.label}</h2>
        </div>
        <button
          type="button"
          aria-label="关闭"
          onClick={onClose}
          className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100"
        >
          ×
        </button>
      </header>
      <p className="mt-3 text-sm text-slate-600">
        Phase 3 会把它变成可对话的 Persona。当下你可以继续点击其他热点感受识别效果。
      </p>
      <p className="mt-2 text-xs text-slate-400">
        confidence ≈ {object.confidence.toFixed(2)} · id {object.id}
      </p>
    </aside>
  );
}
```

- [ ] **Step 4: PersonaPlaceholderPanel 测试通过**

```bash
cd frontend && npm test -- --run src/components/PersonaPlaceholderPanel.test.tsx
```

Expected: 2 PASSED。

- [ ] **Step 5: 写 StudioPage 失败的集成测试**

`frontend/src/pages/StudioPage.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import StudioPage from './StudioPage';

vi.mock('../lib/image/compress', () => ({
  compressIfNeeded: async (f: File) => f,
}));

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
  URL.createObjectURL = vi.fn(() => 'blob:fake') as typeof URL.createObjectURL;
  URL.revokeObjectURL = vi.fn();
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('StudioPage', () => {
  it('上传 → 调用 analyze → 渲染热点 → 点击弹面板', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        request_id: 'req',
        is_safe: true,
        reject_reasons: [],
        scene_summary: 'kitchen',
        objects: [
          {
            id: 'obj_1',
            label: 'cup',
            bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 },
            confidence: 0.9,
          },
        ],
      }),
    );

    render(<StudioPage />);
    const input = screen.getByTestId('upload-input') as HTMLInputElement;
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [file] } });

    const img = await screen.findByRole('img');
    Object.defineProperty(img, 'naturalWidth', { value: 800, configurable: true });
    Object.defineProperty(img, 'naturalHeight', { value: 600, configurable: true });
    Object.defineProperty(img, 'clientWidth', { value: 400, configurable: true });
    Object.defineProperty(img, 'clientHeight', { value: 300, configurable: true });
    img.dispatchEvent(new Event('load'));

    const hotspot = await screen.findByRole('button', { name: /cup/ });
    fireEvent.click(hotspot);
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());
  });

  it('analyze 返回 UNSAFE 时显示错误而不是热点', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        { code: 'UNSAFE_IMAGE', message: '这张图不能用于学习。', details: { reject_reasons: ['face_detected'] } },
        422,
      ),
    );

    render(<StudioPage />);
    const input = screen.getByTestId('upload-input') as HTMLInputElement;
    const file = new File([new Uint8Array(10)], 'a.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByRole('alert')).toHaveTextContent(/不能用于学习/);
  });
});
```

- [ ] **Step 6: 跑测试确认失败**

```bash
cd frontend && npm test -- --run src/pages/StudioPage.test.tsx
```

Expected: 2 项 FAILED(模块未导出)。

- [ ] **Step 7: 写 HomePage 与 StudioPage 实现**

`frontend/src/pages/HomePage.tsx`:

```tsx
import HealthBadge from '../components/HealthBadge';

interface Props {
  onStart: () => void;
}

export default function HomePage({ onStart }: Props) {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-slate-50 px-4 text-slate-900">
      <h1 className="text-4xl font-bold">PersonaLinguaLive</h1>
      <p className="mt-3 max-w-xl text-center text-slate-600">
        Anything you see can teach you English. 上传一张照片,把里面的物体变成英语对话伙伴。
      </p>
      <button
        type="button"
        onClick={onStart}
        className="mt-8 rounded-xl bg-sky-600 px-6 py-3 text-base font-semibold text-white shadow hover:bg-sky-700"
      >
        开始上传
      </button>
      <div className="mt-6">
        <HealthBadge />
      </div>
    </main>
  );
}
```

`frontend/src/pages/StudioPage.tsx`:

```tsx
import { useState } from 'react';
import UploadZone from '../components/UploadZone';
import ImageCanvas, { type ImageReadyInfo } from '../components/ImageCanvas';
import HotspotOverlay from '../components/HotspotOverlay';
import PersonaPlaceholderPanel from '../components/PersonaPlaceholderPanel';
import { analyzeImage, ApiError, type DetectedObject, type VisionAnalyzeResponse } from '../lib/api';
import { compressIfNeeded } from '../lib/image/compress';

type Status =
  | { kind: 'idle' }
  | { kind: 'analyzing' }
  | { kind: 'ready'; result: VisionAnalyzeResponse }
  | { kind: 'error'; message: string };

export default function StudioPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>({ kind: 'idle' });
  const [size, setSize] = useState<ImageReadyInfo | null>(null);
  const [selected, setSelected] = useState<DetectedObject | null>(null);

  async function handleFile(raw: File) {
    setSelected(null);
    setSize(null);
    setStatus({ kind: 'analyzing' });
    try {
      const slim = await compressIfNeeded(raw);
      setFile(slim);
      const result = await analyzeImage(slim);
      setStatus({ kind: 'ready', result });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : '出了点问题,请重试。';
      setStatus({ kind: 'error', message: msg });
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <h1 className="text-2xl font-semibold text-center">Studio</h1>
      <p className="mt-1 mb-6 text-center text-sm text-slate-500">
        选一张照片,看 AI 标出能开口说话的对象。
      </p>

      {!file && <UploadZone onFile={handleFile} />}

      {file && (
        <section className="mx-auto mt-4 w-full max-w-3xl">
          <div className="relative inline-block">
            <ImageCanvas file={file} alt="待分析的图片" onReady={setSize} />
            {status.kind === 'ready' && size && (
              <HotspotOverlay
                renderedWidth={size.renderedWidth}
                renderedHeight={size.renderedHeight}
                objects={status.result.objects}
                onSelect={setSelected}
              />
            )}
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-white"
              onClick={() => {
                setFile(null);
                setStatus({ kind: 'idle' });
                setSelected(null);
                setSize(null);
              }}
            >
              换一张
            </button>
            {status.kind === 'analyzing' && (
              <span className="text-sm text-slate-500">分析中…</span>
            )}
            {status.kind === 'ready' && (
              <span className="text-sm text-slate-500">
                共识别 {status.result.objects.length} 个对象
              </span>
            )}
          </div>

          {status.kind === 'error' && (
            <p role="alert" className="mt-4 text-sm text-rose-600">
              {status.message}
            </p>
          )}
        </section>
      )}

      {selected && (
        <PersonaPlaceholderPanel object={selected} onClose={() => setSelected(null)} />
      )}
    </main>
  );
}
```

- [ ] **Step 8: 修改 `frontend/src/App.tsx` 接入极简哈希路由**

`frontend/src/App.tsx`(完整文件):

```tsx
import { useEffect, useState } from 'react';
import HomePage from './pages/HomePage';
import StudioPage from './pages/StudioPage';

type Route = 'home' | 'studio';

function readRoute(): Route {
  return window.location.hash === '#/studio' ? 'studio' : 'home';
}

export default function App() {
  const [route, setRoute] = useState<Route>(readRoute());

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  if (route === 'studio') return <StudioPage />;
  return (
    <HomePage
      onStart={() => {
        window.location.hash = '#/studio';
      }}
    />
  );
}
```

- [ ] **Step 9: 跑前端全量测试 + lint + 类型检查**

```bash
cd frontend && npm test -- --run
cd frontend && npm run lint
cd frontend && npm run build
```

Expected: 所有 vitest 测试通过;ESLint 0 error;`tsc -b && vite build` 成功。

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/PersonaPlaceholderPanel.tsx \
        frontend/src/components/PersonaPlaceholderPanel.test.tsx \
        frontend/src/pages/HomePage.tsx \
        frontend/src/pages/StudioPage.tsx \
        frontend/src/pages/StudioPage.test.tsx \
        frontend/src/App.tsx
git commit -m "feat(frontend): wire upload → analyze → hotspots → placeholder panel"
```

---

## Task 19: 端到端验证与文档同步

把所有零件合在一起跑一遍,从浏览器视角确认体验,补全 `.env.example` / `README` 的 Phase 2 字段,最后整理一次性 commit。

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: 后端启动开发服务器(默认 fake adapter)**

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Expected: 启动日志看到 `Uvicorn running on http://127.0.0.1:8000`。

- [ ] **Step 2: 在另一终端启动前端**

```bash
cd frontend && npm run dev
```

Expected: Vite 在 5173 端口监听,/api 与 /healthz 通过 vite proxy(若已配置)或 CORS 直连后端。

> 若 vite 还未配 proxy,可在 `frontend/vite.config.ts` 增加:
> ```ts
> server: { proxy: { '/api': 'http://127.0.0.1:8000', '/healthz': 'http://127.0.0.1:8000' } }
> ```
> 这条改动也要在 commit 里。

- [ ] **Step 3: 浏览器访问 http://localhost:5173 走完正例**

- 首页显示标题与"开始上传"按钮,HealthBadge 显示绿色 OK
- 点击"开始上传"进入 #/studio
- 拖一张普通家居 JPEG → 出现"分析中…" → 几百毫秒后图片上叠加 1~12 个蓝色矩形
- 点击任一矩形,右上角弹出 PersonaPlaceholderPanel,显示 label、confidence 与"Phase 3 会把它变成可对话的 Persona"

- [ ] **Step 4: 浏览器侧验证错误分支**

- 拖一张 .heic 文件:UploadZone 就地提示"仅支持 JPEG / PNG / WebP",fetch 没被调用
- 用文件名以 `unsafe_` 开头的 JPEG(命中 FakeAdapter 的 unsafe 触发):弹出"这张图不能用于学习。",不渲染热点
- 短时间内连续点击 ≥6 次"换一张 + 重新上传",会看到 RATE_LIMITED 文案(`429`)

- [ ] **Step 5: 更新 `.env.example`**

把 Phase 2 新增的设置项追加到现有 `.env.example`:

```
# AI / Vision
PLL_AI_VISION_PROVIDER=fake          # fake | openai
PLL_OPENAI_API_KEY=
PLL_OPENAI_VISION_MODEL=gpt-4o-mini
PLL_OPENAI_REQUEST_TIMEOUT_S=20

# Upload limits
PLL_MAX_UPLOAD_MB=8
PLL_ALLOWED_MIME=image/jpeg,image/png,image/webp

# Rate limit
PLL_RATE_LIMIT_PER_MIN=6
```

- [ ] **Step 6: 更新 `README.md`**

在 README 的"开发"或"配置"章节追加一段(若没有就新建一节):

```markdown
## Phase 2:Vision Pipeline

- 默认使用 `fake` Vision Adapter,无需联网即可端到端跑通。
- 切换到 OpenAI:在 `.env` 设置 `PLL_AI_VISION_PROVIDER=openai` 与 `PLL_OPENAI_API_KEY=...`。
- 上传约束:JPEG / PNG / WebP,单张 ≤ 8MB,默认 6 次/分钟/IP。
- Fake Adapter 触发字节前缀(便于本地手动验证):
  - `PLL_FAKE_FACE`:返回 UNSAFE(模拟人脸)
  - `PLL_FAKE_TEXT`:返回 UNSAFE(模拟整页文字)
  - `unsafe_` 文件名前缀同效
```

- [ ] **Step 7: 全量测试 + lint + 构建一次性兜底**

```bash
uv run pytest -v
uv run ruff check app tests
cd frontend && npm test -- --run && npm run lint && npm run build
```

Expected: 全绿。

- [ ] **Step 8: Commit + push**

```bash
git add .env.example README.md frontend/vite.config.ts
git commit -m "docs: document Phase 2 vision pipeline config and behaviors"
git push
```

> 注:若 `frontend/vite.config.ts` 没改,从 `git add` 列表里去掉它。

---

## Phase 2 验收清单

实施完成后,逐项打勾,任一不通过都不能宣布 Phase 2 完成。

### 后端
- [ ] `uv run pytest` 全绿,且至少包含:错误模型、SafetyGuard、VisionService、RateLimiter、Fake/OpenAI Adapter、`/api/vision/analyze` 端到端测试
- [ ] `uv run ruff check app tests` 0 error
- [ ] `Settings` 暴露 `ai_vision_provider / openai_api_key / openai_vision_model / openai_request_timeout_s / max_upload_mb / allowed_mime / rate_limit_per_min`,均带默认值
- [ ] 全局异常处理把 PLLError 映射成统一 JSON,字段固定为 `code / message / request_id`,必要时加 `retry_after`
- [ ] `/api/vision/analyze` 在 fake 模式下成功路径 P50 < 200ms(本机)

### 前端
- [ ] `npm test -- --run` 全绿
- [ ] `npm run lint` 0 error
- [ ] `npm run build` 成功,产物 ≤ 当前 baseline + 50KB(Phase 1 baseline 记在 README)
- [ ] 拖拽与点击两种上传方式都能用,违规文件就地提示
- [ ] 图片渲染保持纵横比,SVG 热点与图像在 resize 后仍然对齐(刷新一次即可,不要求实时 resize)

### 端到端
- [ ] 默认配置(无 OpenAI key)能完整走完"上传 → 热点 → 占位面板"
- [ ] 设置 `PLL_AI_VISION_PROVIDER=openai` + 真实 key 后,同样能跑通(可选,在有 key 的环境验证)
- [ ] 连续高频上传触发 429,前端给出友好提示
- [ ] `.env.example` 与 README 含 Phase 2 配置与切换说明

---

## Phase 2 → Phase 3 衔接备注

- **Persona 数据结构**:Phase 3 接 Persona 之前,在 `app/schemas/` 下新建 `persona.py`,把 `DetectedObject` 当输入,产出 `Persona{id, name, traits, voice}`。本计划没有改动 `vision.py` 的 schema,Phase 3 可以零阻力扩展。
- **占位面板替换**:`PersonaPlaceholderPanel` 是临时件,Phase 3 一旦有 `/api/persona/spawn` 就替换为 `PersonaPanel`。建议保留同样的 props 形状(`object` + `onClose`),把 LLM 调用塞在内部 `useEffect`。
- **配置增项**:Phase 3 会引入 `PLL_AI_LLM_PROVIDER / PLL_OPENAI_LLM_MODEL / PLL_AI_TTS_PROVIDER` 等,本计划已经把"按 provider 派发"模式跑通(VisionFactory),按同一模式新增即可。
- **可观测性**:Phase 4 才上日志/指标,本阶段所有 `logger.info` 已带 `request_id`,方便 Phase 4 直接接采集器。

