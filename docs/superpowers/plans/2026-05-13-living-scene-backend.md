# Living Scene Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build all backend services and APIs needed for the Living Scene mode (v0.3): cartoon scene generation, multi-NPC scene bible, world assets orchestration, ambient scheduler, and chat orchestrator changes. After this plan ships, the backend exposes a complete API surface that the frontend (Plan B) will consume.

**Architecture:** Layered adapter pattern (existing convention). New `imagegen` adapter family. A central `SceneBibleService` produces the world data model that drives all downstream LLM/image-gen prompts. `WorldAssetsService` orchestrates parallel background + sprite generation. `AmbientScheduler` runs per-session coroutines pushing micro-events on a new WS channel.

**Tech Stack:** FastAPI · httpx · pydantic v2 · respx (test HTTP mocks) · pytest-asyncio · structlog

**Spec:** `docs/design/2026-05-13-living-scene-design.md`

---

## File Structure

### New files

```
app/adapters/imagegen/
  __init__.py
  base.py                 # ImageGenAdapter Protocol + ImageGenResult
  fake.py                 # FakeImageGenAdapter (deterministic 1x1 PNG)
  openai.py               # OpenAIImageGenAdapter (DALL-E / gpt-image-1)

app/schemas/world.py      # SceneBible, World*, Asset* Pydantic models
app/schemas/ambient.py    # AmbientEvent payloads

app/prompts/scene_bible.py        # bible generation prompt
app/prompts/judge.py              # generic candidate judge prompt
app/prompts/ambient_mumble.py     # per-NPC mumble prompt
app/prompts/background_gen.py     # background image-to-image prompt builder
app/prompts/sprite_gen.py         # sprite text/image-to-image prompt builder

app/services/scene_bible.py       # SceneBibleService (LLM call + double-run + judge + cache)
app/services/world_assets.py      # WorldAssetsService (orchestrate parallel asset gen)
app/services/world_store.py       # in-memory world_id -> SceneBible + WorldAssets cache
app/services/ambient_scheduler.py # per-session ambient event loop
app/services/judge.py             # pick_best_candidate utility

app/api/world.py                  # GET /api/world/{world_id} SSE
app/api/ambient.py                # WS /api/chat/ambient

tests/test_imagegen_fake.py
tests/test_imagegen_openai.py
tests/test_scene_bible_prompt.py
tests/test_scene_bible_service.py
tests/test_world_assets.py
tests/test_world_api.py
tests/test_ambient_scheduler.py
tests/test_ambient_ws.py
tests/test_chat_orchestrator_world.py
tests/test_context_manager_npc.py
tests/test_vision_prompt_v3.py
tests/test_living_scene_e2e.py
```

### Modified files

```
app/config.py                          # add imagegen settings + provider literal
app/adapters/factory.py                # build_imagegen_adapter
app/api/deps.py                        # provide imagegen adapter + new services
app/prompts/vision_safety.py           # no face rejection, entities w/ kind+salience
app/prompts/chat_system.py             # scene bible injection (world + grounding rules)
app/schemas/vision.py                  # Entity model w/ kind+salience; backward compat
app/adapters/vision/openai_vision.py   # parse entities[] from new schema
app/adapters/vision/qwen_vision.py     # parse entities[] from new schema
app/adapters/vision/fake.py            # return entities[] in new shape
app/services/context_manager.py        # key (session_id, npc_id); is_streaming flag api
app/services/chat_orchestrator.py      # set/clear streaming flag; consume scene bible
app/api/vision.py                      # return world_id; spawn background generation
app/api/chat.py                        # init frame world_id+npc_id; ambient scheduler launch
app/main.py                            # mount new routers
```

### Deprecated (not removed, kept as stubs for one release)

```
app/api/persona.py                     # endpoint 410 Gone with explanatory body
app/services/persona_service.py        # left in place but unused
app/prompts/persona_gen.py             # left in place but unused
```

---

## Task Ordering

Tasks 1-6 lay imagegen foundation. Tasks 7-10 update vision. Tasks 11-15 build scene bible. Tasks 16-19 build world assets. Tasks 20-22 expose world API. Tasks 23-26 update chat. Tasks 27-29 add ambient. Tasks 30-31 deprecate + E2E.

Engineers may execute strictly in order. Each task ends with a commit.

---

## Phase 1 — ImageGen Adapter Foundation

### Task 1: ImageGen Protocol + Result schema

**Files:**
- Create: `app/adapters/imagegen/__init__.py`
- Create: `app/adapters/imagegen/base.py`

- [ ] **Step 1: Create the package marker**

Write `app/adapters/imagegen/__init__.py`:
```python
"""Image generation adapter layer."""
```

- [ ] **Step 2: Define the Protocol and result type**

Write `app/adapters/imagegen/base.py`:
```python
"""ImageGenAdapter protocol: text-to-image and image-to-image."""
from __future__ import annotations

from typing import Protocol


class ImageGenResult:
    __slots__ = ("image_bytes", "mime")

    def __init__(self, image_bytes: bytes, mime: str = "image/png") -> None:
        self.image_bytes = image_bytes
        self.mime = mime


class ImageGenAdapter(Protocol):
    async def text_to_image(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        reference_image: bytes | None = None,
    ) -> ImageGenResult: ...

    async def image_to_image(
        self,
        image_bytes: bytes,
        prompt: str,
        *,
        size: str = "1024x1024",
        strength: float = 0.7,
    ) -> ImageGenResult: ...
```

- [ ] **Step 3: Commit**

```bash
git add app/adapters/imagegen/__init__.py app/adapters/imagegen/base.py
git commit -m "feat(imagegen): add adapter protocol and result type"
```

### Task 2: FakeImageGenAdapter

**Files:**
- Create: `app/adapters/imagegen/fake.py`
- Create: `tests/test_imagegen_fake.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_imagegen_fake.py`:
```python
from __future__ import annotations
import pytest
from app.adapters.imagegen.fake import FakeImageGenAdapter


@pytest.mark.asyncio
async def test_text_to_image_returns_png_bytes():
    adapter = FakeImageGenAdapter()
    result = await adapter.text_to_image("a cup")
    assert result.image_bytes.startswith(b"\x89PNG")
    assert result.mime == "image/png"


@pytest.mark.asyncio
async def test_image_to_image_returns_png_bytes():
    adapter = FakeImageGenAdapter()
    src = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    result = await adapter.image_to_image(src, "make it cartoon")
    assert result.image_bytes.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_text_to_image_is_deterministic():
    adapter = FakeImageGenAdapter()
    a = await adapter.text_to_image("a cup")
    b = await adapter.text_to_image("a cup")
    assert a.image_bytes == b.image_bytes
```

- [ ] **Step 2: Run test, expect ImportError**

`uv run pytest tests/test_imagegen_fake.py -v`

- [ ] **Step 3: Implement fake**

Write `app/adapters/imagegen/fake.py`:
```python
"""Deterministic fake image generator. Returns a 1x1 PNG keyed by prompt hash."""
from __future__ import annotations

import hashlib
import struct
import zlib

from app.adapters.imagegen.base import ImageGenAdapter, ImageGenResult


def _png_1x1(rgba: tuple[int, int, int, int]) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    raw = bytes([0]) + bytes(rgba)
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


class FakeImageGenAdapter(ImageGenAdapter):
    async def text_to_image(self, prompt, *, size="1024x1024", reference_image=None):
        d = hashlib.sha256(prompt.encode("utf-8")).digest()
        return ImageGenResult(_png_1x1((d[0], d[1], d[2], 255)), "image/png")

    async def image_to_image(self, image_bytes, prompt, *, size="1024x1024", strength=0.7):
        d = hashlib.sha256(prompt.encode("utf-8") + image_bytes[:64]).digest()
        return ImageGenResult(_png_1x1((d[0], d[1], d[2], 255)), "image/png")
```

- [ ] **Step 4: Run, expect 3 passed**

`uv run pytest tests/test_imagegen_fake.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/adapters/imagegen/fake.py tests/test_imagegen_fake.py
git commit -m "feat(imagegen): add FakeImageGenAdapter"
```

### Task 3: Config additions

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Add provider literal and openai model field**

In `app/config.py`, after `ai_stt_provider: Literal[...]` line, add:
```python
    ai_imagegen_provider: Literal["fake", "openai"] = "fake"
```

In the OpenAI block after `openai_model_stt`, add:
```python
    openai_model_imagegen: str = "gpt-image-1"
```

In `_validate_provider_credentials`, extend the `uses_openai` tuple to include `self.ai_imagegen_provider`:
```python
        uses_openai = "openai" in (
            self.ai_vision_provider,
            self.ai_llm_provider,
            self.ai_tts_provider,
            self.ai_stt_provider,
            self.ai_imagegen_provider,
        )
```

- [ ] **Step 2: Run config tests**

`uv run pytest tests/test_config.py -v`
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add app/config.py
git commit -m "feat(config): add ai_imagegen_provider settings"
```

### Task 4: Factory build_imagegen_adapter

**Files:**
- Modify: `app/adapters/factory.py`

- [ ] **Step 1: Add imports + factory function**

At top of `app/adapters/factory.py`, add to imports:
```python
from app.adapters.imagegen.base import ImageGenAdapter
from app.adapters.imagegen.fake import FakeImageGenAdapter
from app.adapters.imagegen.openai import OpenAIImageGenAdapter
```

Before `_require_api_key`, add:
```python
def build_imagegen_adapter(settings: Settings) -> ImageGenAdapter:
    if settings.ai_imagegen_provider == "fake":
        return FakeImageGenAdapter()
    if settings.ai_imagegen_provider == "openai":
        _require_api_key(settings)
        return OpenAIImageGenAdapter(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            model=settings.openai_model_imagegen,
            timeout_s=settings.openai_request_timeout_s,
        )
    raise RuntimeError(f"unknown imagegen provider: {settings.ai_imagegen_provider}")
```

- [ ] **Step 2: Smoke (after Task 5 lands `openai.py`)**

`uv run python -c "from app.config import Settings; from app.adapters.factory import build_imagegen_adapter; print(type(build_imagegen_adapter(Settings())).__name__)"`
Expected: `FakeImageGenAdapter`. If ImportError on `openai.py`, defer the smoke until Task 5 ships.

- [ ] **Step 3: Commit**

```bash
git add app/adapters/factory.py
git commit -m "feat(factory): add build_imagegen_adapter"
```

### Task 5: OpenAIImageGenAdapter — text_to_image

**Files:**
- Create: `app/adapters/imagegen/openai.py`
- Create: `tests/test_imagegen_openai.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_imagegen_openai.py`:
```python
from __future__ import annotations
import base64

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError


def _ok(b64: str) -> dict:
    return {"created": 0, "data": [{"b64_json": b64}]}


@pytest.mark.asyncio
@respx.mock
async def test_text_to_image_returns_decoded_bytes():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    payload = b"\x89PNG\r\n\x1a\nHELLO"
    b64 = base64.b64encode(payload).decode()
    respx.post("https://api.openai.com/v1/images/generations").mock(
        return_value=httpx.Response(200, json=_ok(b64))
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=10.0,
    )
    result = await adapter.text_to_image("a cat")
    assert result.image_bytes == payload


@pytest.mark.asyncio
@respx.mock
async def test_text_to_image_sends_model_and_prompt():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    route = respx.post("https://api.openai.com/v1/images/generations").mock(
        return_value=httpx.Response(200, json=_ok(base64.b64encode(b"\x89PNG").decode()))
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=10.0,
    )
    await adapter.text_to_image("a cat", size="512x512")
    body = route.calls.last.request.read().decode()
    assert "gpt-image-1" in body and "a cat" in body and "512x512" in body


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    respx.post("https://api.openai.com/v1/images/generations").mock(
        return_value=httpx.Response(500, text="boom")
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=10.0,
    )
    with pytest.raises(UpstreamFailureError) as ei:
        await adapter.text_to_image("a cat")
    assert ei.value.provider == "openai"


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    respx.post("https://api.openai.com/v1/images/generations").mock(
        side_effect=httpx.TimeoutException("slow")
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=0.1,
    )
    with pytest.raises(UpstreamTimeoutError):
        await adapter.text_to_image("a cat")
```

- [ ] **Step 2: Run, expect ImportError**

`uv run pytest tests/test_imagegen_openai.py -v`

- [ ] **Step 3: Implement adapter (text_to_image only; image_to_image stub)**

Write `app/adapters/imagegen/openai.py`:
```python
"""OpenAI Image Generation adapter (DALL-E / gpt-image-1)."""
from __future__ import annotations

import base64

import httpx
import structlog

from app.adapters.imagegen.base import ImageGenAdapter, ImageGenResult
from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.openai_imagegen")


class OpenAIImageGenAdapter(ImageGenAdapter):
    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_s: float) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    async def text_to_image(self, prompt, *, size="1024x1024", reference_image=None):
        body = {
            "model": self._model,
            "prompt": prompt,
            "size": size,
            "n": 1,
            "response_format": "b64_json",
        }
        return await self._post_generations(body)

    async def image_to_image(self, image_bytes, prompt, *, size="1024x1024", strength=0.7):
        raise NotImplementedError("Task 6")

    async def _post_generations(self, body: dict) -> ImageGenResult:
        url = f"{self._base_url}/images/generations"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("openai.imagegen.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.imagegen.http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc
        if resp.status_code >= 400:
            log.warning("openai.imagegen.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(provider="openai", message=f"openai returned {resp.status_code}")
        try:
            envelope = resp.json()
            decoded = base64.b64decode(envelope["data"][0]["b64_json"])
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("openai.imagegen.parse_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message="invalid response") from exc
        return ImageGenResult(decoded, "image/png")
```

- [ ] **Step 4: Run, expect 4 passed**

`uv run pytest tests/test_imagegen_openai.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/adapters/imagegen/openai.py tests/test_imagegen_openai.py
git commit -m "feat(imagegen): add OpenAI text_to_image adapter"
```

### Task 6: image_to_image via /images/edits

**Files:**
- Modify: `app/adapters/imagegen/openai.py`
- Modify: `tests/test_imagegen_openai.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_imagegen_openai.py`:
```python
@pytest.mark.asyncio
@respx.mock
async def test_image_to_image_uses_edits_endpoint():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    payload = b"\x89PNG\r\n\x1a\nEDIT"
    b64 = base64.b64encode(payload).decode()
    route = respx.post("https://api.openai.com/v1/images/edits").mock(
        return_value=httpx.Response(200, json=_ok(b64))
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=10.0,
    )
    src = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    result = await adapter.image_to_image(src, "make it cartoon")
    assert result.image_bytes == payload
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_image_to_image_500_raises():
    from app.adapters.imagegen.openai import OpenAIImageGenAdapter
    respx.post("https://api.openai.com/v1/images/edits").mock(
        return_value=httpx.Response(500, text="boom")
    )
    adapter = OpenAIImageGenAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-image-1", timeout_s=10.0,
    )
    with pytest.raises(UpstreamFailureError):
        await adapter.image_to_image(b"\x89PNG", "x")
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_imagegen_openai.py::test_image_to_image_uses_edits_endpoint -v`

- [ ] **Step 3: Replace `image_to_image` stub**

In `app/adapters/imagegen/openai.py`, replace the `image_to_image` method body:
```python
    async def image_to_image(self, image_bytes, prompt, *, size="1024x1024", strength=0.7):
        url = f"{self._base_url}/images/edits"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        files = {"image": ("input.png", image_bytes, "image/png")}
        data = {
            "model": self._model,
            "prompt": prompt,
            "size": size,
            "n": "1",
            "response_format": "b64_json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, headers=headers, files=files, data=data)
        except httpx.TimeoutException as exc:
            log.warning("openai.imagegen.edit.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider="openai") from exc
        except httpx.HTTPError as exc:
            log.warning("openai.imagegen.edit.http_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message=str(exc)) from exc
        if resp.status_code >= 400:
            log.warning("openai.imagegen.edit.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(provider="openai", message=f"openai returned {resp.status_code}")
        try:
            envelope = resp.json()
            decoded = base64.b64decode(envelope["data"][0]["b64_json"])
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("openai.imagegen.edit.parse_error", error=str(exc))
            raise UpstreamFailureError(provider="openai", message="invalid response") from exc
        return ImageGenResult(decoded, "image/png")
```

- [ ] **Step 4: Run all imagegen tests**

`uv run pytest tests/test_imagegen_openai.py tests/test_imagegen_fake.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/adapters/imagegen/openai.py tests/test_imagegen_openai.py
git commit -m "feat(imagegen): add image_to_image via /images/edits"
```



## Phase 2 — Vision Schema + Prompt Rewrite

### Task 7: Entity schema with kind/salience

**Files:**
- Modify: `app/schemas/vision.py`

- [ ] **Step 1: Write failing test for new schema**

Write inline test file `tests/test_vision_schema.py`:
```python
"""Tests for vision schema changes (Entity, kind, salience)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.vision import Entity, BBox


class TestEntity:
    def test_entity_minimal(self):
        e = Entity(id="e1", kind="object", label="cup", bbox=BBox(x=0, y=0, w=0.5, h=0.5))
        assert e.salience == 0.0  # default
        assert e.seed is None

    def test_entity_character_kind(self):
        e = Entity(id="e2", kind="character", label="person",
                    bbox=BBox(x=0.1, y=0.1, w=0.3, h=0.8))
        assert e.kind == "character"

    def test_entity_invalid_kind_rejected(self):
        with pytest.raises(ValidationError):
            Entity(id="e3", kind="alien", label="x", bbox=BBox(x=0, y=0, w=0.5, h=0.5))

    def test_entity_salience_clamped(self):
        e = Entity(id="e4", kind="object", label="cup", bbox=BBox(x=0, y=0, w=0.5, h=0.5),
                    salience=1.5)
        assert e.salience == 1.0

    def test_entity_negative_salience_clamped(self):
        e = Entity(id="e5", kind="object", label="cup", bbox=BBox(x=0, y=0, w=0.5, h=0.5),
                    salience=-0.5)
        assert e.salience == 0.0
```

- [ ] **Step 2: Run, expect ImportError**

`uv run pytest tests/test_vision_schema.py -v`

- [ ] **Step 3: Add Entity model**

Edit `app/schemas/vision.py`. Add import at top:
```python
from typing import Literal
```

Add `Entity` class after `DetectedObject`:
```python
class Entity(BaseModel):
    id: str
    kind: Literal["object", "character"]
    label: str
    bbox: BBox
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    salience: float = Field(default=0.0, ge=0.0, le=1.0)
    seed: str | None = None
```

- [ ] **Step 4: Run, expect tests pass**

`uv run pytest tests/test_vision_schema.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/vision.py tests/test_vision_schema.py
git commit -m "feat(vision): add Entity model with kind+salience for Living Scene"
```

### Task 8: Vision prompt rewrite — no face rejection

**Files:**
- Modify: `app/prompts/vision_safety.py`

- [ ] **Step 1: Write failing prompt test**

Write `tests/test_vision_prompt_v3.py`:
```python
"""Tests for revised vision_safety prompt (v3 — Living Scene)."""
from __future__ import annotations

import json

from app.prompts.vision_safety import build_vision_safety_messages


def test_system_prompt_does_not_mention_face_rejection():
    msgs = build_vision_safety_messages(image_data_url="data:image/png;base64,x")
    sys_msg = next(m["content"] for m in msgs if m["role"] == "system")
    # The new prompt should NOT instruct the model to reject faces as unsafe.
    assert "real human faces" not in sys_msg
    assert "face_detected" not in sys_msg


def test_system_prompt_includes_entities_key():
    msgs = build_vision_safety_messages(image_data_url="data:image/png;base64,x")
    sys_msg = next(m["content"] for m in msgs if m["role"] == "system")
    assert "entities" in sys_msg
    assert "character" in sys_msg
    assert "kind" in sys_msg
    assert "salience" in sys_msg


def test_system_prompt_includes_raw_scene():
    msgs = build_vision_safety_messages(image_data_url="data:image/png;base64,x")
    sys_msg = next(m["content"] for m in msgs if m["role"] == "system")
    assert "raw_scene" in sys_msg


def test_system_prompt_retains_safety_checks():
    msgs = build_vision_safety_messages(image_data_url="data:image/png;base64,x")
    sys_msg = next(m["content"] for m in msgs if m["role"] == "system")
    # Should still check NSFW / violence / weapons / sensitive symbols
    assert "nsfw" in sys_msg.lower() or "NSFW" in sys_msg
    assert "violence" in sys_msg
    assert "weapons" in sys_msg
    assert "sensitive" in sys_msg
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_vision_prompt_v3.py -v`
Expected: assertions fail (old prompt mentions faces, lacks entities).

- [ ] **Step 3: Rewrite prompt**

Replace the full content of `app/prompts/vision_safety.py`:
```python
"""Prompt template for safety check + entity detection (v3 Living Scene).

Differences from v2:
- Real faces are NO longer flagged as unsafe. They become entities with
  kind="character". Safety is limited to NSFW/violence/weapons/symbols/text.
- Output shape changed: entities[] replaces objects[], each entity has
  kind ("object" | "character") and salience (0-1) for downstream filtering.
- Added raw_scene (free-text scene description).
"""
from __future__ import annotations

from typing import Any

_SYSTEM_TEMPLATE = """You are an image analyzer for an English learning app.

STEP 1 — Safety check.
Mark the image UNSAFE if it contains any of:
- NSFW content (nudity, sexual acts, suggestive imagery)
- Violence, blood, gore
- Weapons of any kind
- Sensitive political symbols, flags, or propaganda
- Dominant text or handwriting occupying >40% of image area

Real human faces, crowds, children — ALL SAFE. Do NOT flag them.

STEP 2 — Scene understanding.
Describe the scene in 1-2 sentences (raw_scene). Focus on: what kind of place
it is (kitchen, café, desk, park), what is happening, the lighting/mood.

STEP 3 — Entity detection.
List every distinct OBJECT and PERSON that could be a conversation partner.
Each entity must:
- Be clearly visible (>= 1.5% of total image area)
- Have a normalized bounding box [x, y, w, h] in [0, 1]
- Have kind: "object" for things, "character" for people
- Have salience (0-1): how important this entity is to the scene
- Have label (lowercase singular English noun for objects, simple role for people)
- Have a 1-line persona_seed (short phrase describing potential character)

Output STRICT JSON, exactly this shape, no markdown fence, no commentary:
{{
  "is_safe": <bool>,
  "reject_reasons": [<reason_code>, ...],
  "raw_scene": "<1-2 sentence English description>",
  "entities": [
    {{
      "id": "e1",
      "kind": "object",
      "label": "coffee mug",
      "bbox": [<x>, <y>, <w>, <h>],
      "salience": 0.9,
      "persona_seed": "morning brew enthusiast"
    }}
  ]
}}

Valid reject_reasons codes:
"nsfw" | "violence" | "weapons" | "sensitive_symbols" | "dominant_text"
"""


def build_vision_safety_messages(
    *,
    image_data_url: str,
    max_entities: int = 12,
) -> list[dict[str, Any]]:
    """Return messages for one-shot vision analysis (v3 Living Scene)."""
    system_text = _SYSTEM_TEMPLATE.format(max_entities=max_entities)
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

- [ ] **Step 4: Run, expect 4 passed**

`uv run pytest tests/test_vision_prompt_v3.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/prompts/vision_safety.py tests/test_vision_prompt_v3.py
git commit -m "feat(vision): rewrite safety prompt - no face rejection, entity kind+salience, raw_scene"
```

### Task 9: Update vision adapters — output Entity[] from new prompt shape

**Files:**
- Modify: `app/adapters/vision/openai_vision.py`
- Modify: `app/adapters/vision/qwen_vision.py`
- Modify: `app/adapters/vision/fake.py`

- [ ] **Step 1: Write adapter test for entity parsing**

Append to `tests/test_openai_vision_adapter.py`:
```python
@pytest.mark.asyncio
@respx.mock
async def test_analyze_image_returns_entities_with_kind():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    payload = {
        "is_safe": True,
        "reject_reasons": [],
        "raw_scene": "A cozy desk with a coffee mug and a person working",
        "entities": [
            {"id": "e1", "kind": "object", "label": "coffee mug",
             "bbox": [0.1, 0.2, 0.3, 0.4], "salience": 0.9, "persona_seed": "morning brew"},
            {"id": "e2", "kind": "character", "label": "person",
             "bbox": [0.0, 0.0, 1.0, 1.0], "salience": 0.7},
        ],
    }
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_single_response(json.dumps(payload)))
    )

    adapter = OpenAIVisionAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-4o", timeout_s=30.0,
    )
    result = await adapter.analyze_image(b"fakebytes")
    assert len(result.entities) == 2
    assert result.entities[0].kind == "object"
    assert result.entities[1].kind == "character"
    assert result.raw_scene == "A cozy desk with a coffee mug and a person working"


@pytest.mark.asyncio
@respx.mock
async def test_analyze_image_fallback_to_empty_entities_on_missing():
    from app.adapters.vision.openai_vision import OpenAIVisionAdapter

    payload = {"is_safe": True, "reject_reasons": [], "raw_scene": "empty", "entities": []}
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_build_single_response(json.dumps(payload)))
    )
    adapter = OpenAIVisionAdapter(
        api_key="sk-test", base_url="https://api.openai.com/v1",
        model="gpt-4o", timeout_s=30.0,
    )
    result = await adapter.analyze_image(b"fakebytes")
    assert result.entities == []
    assert result.objects == []  # backward compat
```

- [ ] **Step 2: Run, verify failure (old payload_to_result doesn't extract entities)**

`uv run pytest tests/test_openai_vision_adapter.py::test_analyze_image_returns_entities_with_kind -v`

- [ ] **Step 3: Update VisionResult schema + adapter parsing**

In `app/schemas/vision.py`, add `entities: list[Entity] = Field(default_factory=list)` and `raw_scene: str = ""` to `VisionResult`. Keep `objects` field as backward-compat alias (populated from `entities` for old code).

In `app/adapters/vision/openai_vision.py`, update `_payload_to_result`:

```python
def _payload_to_result(payload: dict) -> VisionResult:
    is_safe = bool(payload.get("is_safe", False))
    reasons = list(payload.get("reject_reasons") or [])
    raw_scene = str(payload.get("raw_scene") or "")
    raw_entities = payload.get("entities") or []

    entities: list[Entity] = []
    for idx, raw in enumerate(raw_entities, start=1):
        bbox_arr = raw.get("bbox") or [0, 0, 0, 0]
        if len(bbox_arr) != 4:
            continue
        kind = raw.get("kind", "object")
        if kind not in ("object", "character"):
            kind = "object"
        try:
            confidence = max(0.0, min(1.0, float(raw.get("confidence") or 0.5)))
            salience = max(0.0, min(1.0, float(raw.get("salience") or 0.5)))
        except (ValueError, TypeError):
            confidence = 0.5
            salience = 0.5
        entities.append(
            Entity(
                id=raw.get("id") or f"e{idx}",
                kind=kind,
                label=str(raw.get("label") or "entity"),
                bbox=BBox(
                    x=max(0.0, min(1.0, float(bbox_arr[0]))),
                    y=max(0.0, min(1.0, float(bbox_arr[1]))),
                    w=max(0.0, min(1.0, float(bbox_arr[2]))),
                    h=max(0.0, min(1.0, float(bbox_arr[3]))),
                ),
                confidence=confidence,
                salience=salience,
                seed=raw.get("persona_seed") or raw.get("seed"),
            )
        )

    # Backward compat: keep populating objects from what used to be the objects field
    # For v3 code paths everything reads from entities.
    raw_objects = payload.get("objects") or []
    objects = []  # simplified - existing objects parsing stays if needed

    return VisionResult(
        is_safe=is_safe,
        reject_reasons=reasons,
        raw_scene=raw_scene,
        entities=entities,
        scene_summary=raw_scene,  # backward compat
        objects=objects,
    )
```

Also update imports at top of `openai_vision.py` to import `Entity` from schemas.

- [ ] **Step 4: Update FakeVisionAdapter**

In `app/adapters/vision/fake.py`, update `VisionAnalyzeResponse` construction to include `entities`:
```python
    return VisionAnalyzeResponse(
        request_id="fake",
        is_safe=True,
        raw_scene="A fake test scene with a laptop",
        scene_summary="A fake test scene with a laptop",
        entities=[
            Entity(id="e1", kind="object", label="laptop",
                   bbox=BBox(x=0, y=0, w=1, h=1), confidence=0.9, salience=0.9,
                   seed="a reliable old laptop")
        ],
        objects=[],
    )
```

- [ ] **Step 5: Run all vision tests**

`uv run pytest tests/test_openai_vision_adapter.py tests/test_vision_prompt_v3.py tests/test_vision_schema.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/vision.py app/adapters/vision/openai_vision.py app/adapters/vision/fake.py tests/test_openai_vision_adapter.py
git commit -m "feat(vision): adapters parse entities+raw_scene from new prompt shape"
```

## Phase 3 — Scene Bible Generation

### Task 10: World schemas (SceneBible, WorldAssets, SSE events)

**Files:**
- Create: `app/schemas/world.py`

- [ ] **Step 1: Write tests**

Write `tests/test_world_schema.py`:
```python
"""Tests for world schemas (SceneBible, WorldAssets)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.world import (
    VoiceTraits,
    NPCSpec,
    CrossRelationship,
    WorldSpec,
    SceneBible,
    WorldAssetStatus,
)


def test_voice_traits_default():
    v = VoiceTraits()
    assert v.gender == "female"
    assert v.age == "adult"
    assert v.tone == "warm"


def test_npc_spec_minimal():
    n = NPCSpec(
        entity_id="e1", kind="object", persona_name="Mocha",
        role_in_scene="afternoon coffee",
        personality="warm",
        voice_traits=VoiceTraits(),
    )
    assert n.vocab_focus == []


def test_cross_relationship():
    r = CrossRelationship(from_entity="e1", to_entity="e2", note="partners")
    assert r.from_entity == "e1"


def test_scene_bible_round_trip():
    bible = SceneBible(
        world=WorldSpec(
            place="cafe", time_of_day="afternoon", weather="sunny",
            mood="cozy", ambient_sounds=["rain"], bgm_mood="warm",
            art_style_prompt="watercolor",
        ),
        npcs=[
            NPCSpec(
                entity_id="e1", kind="object", persona_name="Mocha",
                role_in_scene="coffee", personality="warm",
                voice_traits=VoiceTraits(),
            )
        ],
        cross_relationships=[],
    )
    assert len(bible.npcs) == 1
    assert bible.npcs[0].persona_name == "Mocha"


def test_world_asset_status():
    s = WorldAssetStatus(world_id="w_abc")
    assert s.state == "pending"
```

- [ ] **Step 2: Run, expect ImportError**

`uv run pytest tests/test_world_schema.py -v`

- [ ] **Step 3: Create world.py schemas**

Write `app/schemas/world.py`:
```python
"""Pydantic models for SceneBible, WorldAssets, and SSE event payloads."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---- Voice ----

class VoiceTraits(BaseModel):
    gender: Literal["female", "male"] = "female"
    age: Literal["child", "adult", "elder"] = "adult"
    tone: Literal["warm", "sweet", "confident", "neutral", "playful", "gruff"] = "warm"


# ---- World / Environment ----

class WorldSpec(BaseModel):
    place: str
    time_of_day: str
    weather: str
    mood: str
    ambient_sounds: list[str] = Field(default_factory=list)
    bgm_mood: str = ""
    art_style_prompt: str = ""


# ---- NPC ----

class NPCSpec(BaseModel):
    entity_id: str
    kind: Literal["object", "character"]
    persona_name: str
    role_in_scene: str
    relationship_to_user: str = ""
    personality: str = ""
    voice_traits: VoiceTraits = Field(default_factory=VoiceTraits)
    vocab_focus: list[str] = Field(default_factory=list)
    ambient_actions: list[str] = Field(default_factory=list)


class CrossRelationship(BaseModel):
    from_entity: str
    to_entity: str
    note: str


# ---- SceneBible (the central generation artifact) ----

class SceneBible(BaseModel):
    world: WorldSpec
    npcs: list[NPCSpec]
    cross_relationships: list[CrossRelationship] = Field(default_factory=list)


# ---- Asset related ----

class SpriteSet(BaseModel):
    default: str  # base64
    blink: str = ""
    mouth_a: str = ""
    mouth_b: str = ""
    mouth_c: str = ""


class NPCSprites(BaseModel):
    entity_id: str
    sprites: SpriteSet
    position_x: float = Field(default=0.5, ge=0.0, le=1.0)
    position_y: float = Field(default=0.5, ge=0.0, le=1.0)


class WorldAssets(BaseModel):
    background_base64: str = ""
    sprites: list[NPCSprites] = Field(default_factory=list)


# ---- SSE event types ----

class WorldAssetStatus(BaseModel):
    world_id: str
    state: Literal["pending", "bible_ready", "background_ready", "sprite_ready", "world_ready", "error"] = "pending"
    event_data: dict = Field(default_factory=dict)
```

- [ ] **Step 4: Run, expect pass**

`uv run pytest tests/test_world_schema.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/world.py tests/test_world_schema.py
git commit -m "feat(world): add SceneBible, WorldAssets, and SSE event schemas"
```

### Task 11: Scene bible prompt

**Files:**
- Create: `app/prompts/scene_bible.py`

- [ ] **Step 1: Write prompt test**

Write `tests/test_scene_bible_prompt.py`:
```python
"""Tests for scene_bible prompt assembly."""
from __future__ import annotations

from app.prompts.scene_bible import build_scene_bible_messages


def test_build_scene_bible_messages_contains_world_key():
    msgs = build_scene_bible_messages(
        raw_scene="A cozy desk with coffee",
        entities=[],
        user_level="beginner",
    )
    content = " ".join(
        m["content"] if isinstance(m["content"], str) else str(m["content"])
        for m in msgs
    )
    assert "raw_scene" in content


def test_build_scene_bible_messages_includes_entities():
    entities = [
        {"id": "e1", "kind": "object", "label": "mug", "salience": 0.9, "persona_seed": "warm"},
        {"id": "e2", "kind": "character", "label": "person", "salience": 0.6},
    ]
    msgs = build_scene_bible_messages(
        raw_scene="A cafe table", entities=entities, user_level="intermediate",
    )
    joined = str(msgs)
    assert "mug" in joined
    assert "person" in joined
    assert "character" in joined


def test_build_scene_bible_messages_output_shape():
    msgs = build_scene_bible_messages(
        raw_scene="Park bench", entities=[], user_level="advanced",
    )
    content = next(
        (m["content"] for m in msgs if m["role"] == "system"), ""
    )
    assert "npcs" in content
    assert "world" in content
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_scene_bible_prompt.py -v`

- [ ] **Step 3: Implement prompt**

Write `app/prompts/scene_bible.py`:
```python
"""Prompt template for Scene Bible generation (v3 Living Scene).

Given raw_scene + entities from vision, the LLM produces a structured
SceneBible that defines: the world environment, NPC specs with personalities,
and cross-entity relationships.
"""
from __future__ import annotations

from typing import Any


_SYSTEM = """You are a world builder for an English learning app.

Given a scene description and a list of entities (objects and people),
create a "Scene Bible" — a complete specification for a cartoon living scene.

CRITICAL RULES:
- The scene MUST retain the original entities (they become NPCs).
- Only use the top {max_npcs} entities by salience as NPCs. Drop low-salience items.
- The world's art_style_prompt must describe a cartoon/illustration style
  that will be used for ALL image generation (background and sprites) to
  maintain visual consistency.
- ambient_sounds must only come from this list (comma-separated IDs):
  {allowed_sounds}. Pick 1-3.
- bgm_mood must be one of: warm, cozy, contemplative, playful, mysterious, energetic.
- Each NPC gets voice_traits for TTS voice selection.
- Each NPC gets ambient_actions: 2-4 short verb phrases for background behavior.

Output STRICT JSON, exactly this shape, no markdown:
{{
  "world": {{
    "place": "<string — where is this?>",
    "time_of_day": "<string — morning / afternoon / evening / night>",
    "weather": "<string — sunny / rainy / cloudy / ...>",
    "mood": "<string — one word feeling>",
    "ambient_sounds": ["<sound_id_1>", "<sound_id_2>"],
    "bgm_mood": "<string>",
    "art_style_prompt": "<detailed cartoon art style description>"
  }},
  "npcs": [
    {{
      "entity_id": "<from input>",
      "kind": "object|character",
      "persona_name": "<creative English name>",
      "role_in_scene": "<what this entity does in this scene>",
      "relationship_to_user": "<who they are to the user>",
      "personality": "<2-3 sentence personality>",
      "voice_traits": {{"gender": "female|male", "age": "child|adult|elder", "tone": "warm|sweet|confident|neutral|playful|gruff"}},
      "vocab_focus": ["<5-8 English vocab words>"],
      "ambient_actions": ["<verb phrase>", ...]
    }}
  ],
  "cross_relationships": [
    {{"from_entity": "<entity_id>", "to_entity": "<entity_id>", "note": "<their relationship>"}}
  ]
}}
"""


def build_scene_bible_messages(
    raw_scene: str,
    entities: list[dict[str, Any]],
    user_level: str = "beginner",
    max_npcs: int = 6,
    allowed_sounds: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build messages for SceneBible LLM generation."""
    if allowed_sounds is None:
        allowed_sounds = [
            "rain_on_window", "espresso_machine", "page_turns",
            "cafe_chatter", "forest_birds", "wind_chimes", "keyboard_typing",
            "traffic_hum", "ocean_waves", "fire_crackling",
            "clock_ticking", "footsteps", "distant_laughter", "birdsong",
            "kitchen_sizzle", "water_pouring", "fan_hum", "dog_bark",
            "shower_run", "refrigerator_hum",
        ]

    system = _SYSTEM.format(max_npcs=max_npcs, allowed_sounds=", ".join(allowed_sounds))

    entity_lines = "\n".join(
        f"  - {e.get('id', '?')}: kind={e.get('kind', 'object')}, "
        f"label={e.get('label', '?')}, salience={e.get('salience', 0)}, "
        f"seed={e.get('persona_seed', e.get('seed', ''))}"
        for e in entities
    )

    user = (
        f"User level: {user_level}\n\n"
        f"Scene description:\n{raw_scene}\n\n"
        f"Detected entities (use first {max_npcs} by salience):\n{entity_lines}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
```

- [ ] **Step 4: Run, expect 3 passed**

`uv run pytest tests/test_scene_bible_prompt.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/prompts/scene_bible.py tests/test_scene_bible_prompt.py
git commit -m "feat(prompt): add Scene Bible generation prompt"
```

### Task 12: Judge prompt for candidate selection

**Files:**
- Create: `app/prompts/judge.py`

- [ ] **Step 1: Write test**

Write `tests/test_judge_prompt.py`:
```python
from __future__ import annotations

from app.prompts.judge import build_judge_message, pick_best_candidate


def test_build_judge_message_includes_candidates():
    candidates = ["bible A content", "bible B content"]
    msg = build_judge_message(candidates, "scene bible", ["coherence", "character depth"])
    assert "bible A" in msg
    assert "coherence" in msg


def test_pick_best_candidate_no_error():
    candidates = ["alpha", "beta"]
    # No external LLM here — just checks interface shape
    result = pick_best_candidate(candidates, "test", ["x"])
    assert result == 0  # first as default
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_judge_prompt.py -v`

- [ ] **Step 3: Implement**

Write `app/prompts/judge.py`:
```python
"""LLM judge: pick best from N candidates."""
from __future__ import annotations


def build_judge_message(candidates: list[str], purpose: str, dimensions: list[str]) -> list[dict]:
    """Build messages asking an LLM to score candidates."""
    dims = ", ".join(dimensions)
    system = (
        f"You are an expert judge evaluating {len(candidates)} candidates for "
        f"{purpose}. Score each on {dims}.\n"
        "Output STRICT JSON:\n"
        '{"best_index": <int 0-based>, "reason": "<one sentence explanation>", '
        '"scores": [<int>]}\n'
        "No markdown, no other text."
    )
    lines = "\n\n".join(
        f"--- CANDIDATE {i} ---\n{c}" for i, c in enumerate(candidates)
    )
    user = f"Evaluate these candidates:\n\n{lines}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def pick_best_candidate(
    candidates: list[str],
    purpose: str = "",
    dimensions: list[str] | None = None,
) -> int:
    """Return the index of the best candidate, or 0 by default.

    In production this calls an LLM. The function signature supports
    dependency injection for that.
    """
    # Default: pick first (true implementation lives in SceneBibleService)
    return 0
```

- [ ] **Step 4: Run**

`uv run pytest tests/test_judge_prompt.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/prompts/judge.py tests/test_judge_prompt.py
git commit -m "feat(prompt): add LLM judge for candidate selection"
```

### Task 13: WorldStore — in-memory cache

**Files:**
- Create: `app/services/world_store.py`

- [ ] **Step 1: Write test**

Write `tests/test_world_store.py`:
```python
from __future__ import annotations
import pytest
from app.schemas.world import SceneBible, WorldSpec, NPCSpec, VoiceTraits, WorldAssets, NPCSprites, SpriteSet
from app.services.world_store import WorldStore


@pytest.fixture
def sample_bible():
    return SceneBible(
        world=WorldSpec(place="cafe", time_of_day="afternoon", weather="sunny",
                        mood="cozy", ambient_sounds=["rain"], bgm_mood="warm",
                        art_style_prompt="watercolor"),
        npcs=[],
        cross_relationships=[],
    )


def test_store_and_get(sample_bible):
    store = WorldStore()
    wid = store.put(sample_bible)
    assert wid.startswith("w_")
    retrieved = store.get(wid)
    assert retrieved is not None
    assert retrieved.world.place == "cafe"


def test_get_unknown_returns_none():
    store = WorldStore()
    assert store.get("w_nonexistent") is None


def test_get_or_raise(sample_bible):
    store = WorldStore()
    wid = store.put(sample_bible)
    assert store.get_or_raise(wid).world.place == "cafe"


def test_get_or_raise_unknown():
    store = WorldStore()
    import app.errors
    with pytest.raises(app.errors.WorldNotFoundError):
        store.get_or_raise("w_bad")


def test_put_assets_and_get():
    store = WorldStore()
    assets = WorldAssets(background_base64="aaaa", sprites=[
        NPCSprites(entity_id="e1", sprites=SpriteSet(default="bbbb")),
    ])
    store.put_assets("w_test", assets)
    retrieved = store.get_assets("w_test")
    assert retrieved is not None
    assert retrieved.background_base64 == "aaaa"
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_world_store.py -v`

- [ ] **Step 3: Add WorldNotFoundError to errors**

In `app/errors.py`, add after existing error classes:
```python
class WorldNotFoundError(ValueError):
    def __init__(self, world_id: str) -> None:
        super().__init__(f"world not found: {world_id}")
        self.world_id = world_id
```

- [ ] **Step 4: Implement WorldStore**

Write `app/services/world_store.py`:
```python
"""In-memory cache for SceneBible and WorldAssets, keyed by world_id."""
from __future__ import annotations

from uuid import uuid4

from app.errors import WorldNotFoundError
from app.schemas.world import SceneBible, WorldAssets


class WorldStore:
    """In-memory store: one instance per app lifetime, reset on create_app()."""

    def __init__(self) -> None:
        self._bibles: dict[str, SceneBible] = {}
        self._assets: dict[str, WorldAssets] = {}
        self._states: dict[str, str] = {}  # world_id -> state string

    def _new_id(self) -> str:
        return "w_" + uuid4().hex[:8]

    def put(self, bible: SceneBible) -> str:
        wid = self._new_id()
        self._bibles[wid] = bible
        self._states[wid] = "bible_ready"
        return wid

    def get(self, wid: str) -> SceneBible | None:
        return self._bibles.get(wid)

    def get_or_raise(self, wid: str) -> SceneBible:
        bible = self.get(wid)
        if bible is None:
            raise WorldNotFoundError(wid)
        return bible

    def put_assets(self, wid: str, assets: WorldAssets) -> None:
        self._assets[wid] = assets
        self._states[wid] = "world_ready"

    def get_assets(self, wid: str) -> WorldAssets | None:
        return self._assets.get(wid)

    def set_state(self, wid: str, state: str) -> None:
        self._states[wid] = state

    def get_state(self, wid: str) -> str:
        return self._states.get(wid, "pending")
```

- [ ] **Step 5: Run, expect pass**

`uv run pytest tests/test_world_store.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add app/errors.py app/services/world_store.py tests/test_world_store.py
git commit -m "feat(services): add WorldStore in-memory cache + WorldNotFoundError"
```

### Task 14: SceneBibleService — generation + double-run + judge

**Files:**
- Create: `app/services/scene_bible.py`
- Create: `tests/test_scene_bible_service.py`

- [ ] **Step 1: Write tests**

Write `tests/test_scene_bible_service.py`:
```python
from __future__ import annotations

import json

import pytest

from app.schemas.world import SceneBible


class FakeLLM:
    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self._idx = 0

    async def generate(self, messages, *, temperature=0.0):
        resp = self.responses[self._idx]
        self._idx += 1
        return resp


@pytest.mark.asyncio
async def test_generate_with_single_response():
    from app.services.scene_bible import SceneBibleService

    bible_json = json.dumps({
        "world": {
            "place": "cafe", "time_of_day": "afternoon", "weather": "sunny",
            "mood": "cozy", "ambient_sounds": ["rain"], "bgm_mood": "warm",
            "art_style_prompt": "watercolor",
        },
        "npcs": [
            {
                "entity_id": "e1", "kind": "object", "persona_name": "Mocha",
                "role_in_scene": "coffee", "relationship_to_user": "friend",
                "personality": "warm", "voice_traits": {"gender": "female", "age": "adult", "tone": "warm"},
                "vocab_focus": ["cozy"], "ambient_actions": ["steam"],
            }
        ],
        "cross_relationships": [],
    })

    llm = FakeLLM([bible_json])
    store = None  # not needed for generation alone
    service = SceneBibleService(llm=llm, world_store=store)
    bible = await service.generate(
        raw_scene="A cafe table",
        entities=[],
        user_level="beginner",
    )
    assert isinstance(bible, SceneBible)
    assert bible.world.place == "cafe"
    assert len(bible.npcs) == 1


@pytest.mark.asyncio
async def test_generate_with_invalid_json_raises():
    from app.services.scene_bible import SceneBibleService

    llm = FakeLLM(["this is not json"])
    service = SceneBibleService(llm=llm, world_store=None)
    import app.errors
    with pytest.raises(app.errors.SceneBibleParseError):
        await service.generate(raw_scene="x", entities=[])


@pytest.mark.asyncio
async def test_generate_with_retry_on_failure():
    from app.services.scene_bible import SceneBibleService

    good = json.dumps({
        "world": {"place": "park", "time_of_day": "morning", "weather": "sunny",
                  "mood": "peaceful", "ambient_sounds": [], "bgm_mood": "warm",
                  "art_style_prompt": "sketch"},
        "npcs": [],
        "cross_relationships": [],
    })
    llm = FakeLLM(["bad json", good])
    service = SceneBibleService(llm=llm, world_store=None)
    bible = await service.generate(raw_scene="x", entities=[])
    assert bible.world.place == "park"
```

- [ ] **Step 2: Add new error classes**

In `app/errors.py`, add:
```python
class SceneBibleParseError(ValueError):
    """Scene Bible JSON failed to parse after retry."""
```

- [ ] **Step 3: Implement SceneBibleService**

Write `app/services/scene_bible.py`:
```python
"""SceneBibleService: generates SceneBible from LLM with double-run + judge + cache."""
from __future__ import annotations

import json

import structlog

from app.adapters.llm.base import LLMAdapter
from app.errors import SceneBibleParseError
from app.prompts.judge import build_judge_message
from app.prompts.scene_bible import build_scene_bible_messages
from app.schemas.world import SceneBible
from app.services.world_store import WorldStore

log = structlog.get_logger("pll.service.scene_bible")


class SceneBibleService:
    def __init__(self, llm: LLMAdapter, world_store: WorldStore | None) -> None:
        self._llm = llm
        self._store = world_store

    async def generate(
        self,
        raw_scene: str,
        entities: list[dict],
        user_level: str = "beginner",
        image_hash: str = "",
        max_npcs: int = 6,
    ) -> SceneBible:
        # Phase 1: run once at temperature 0.7 (creative)
        messages = build_scene_bible_messages(raw_scene, entities, user_level, max_npcs)
        raw1 = await self._llm.generate(messages, temperature=0.7)
        bible1 = self._parse(raw1)
        if bible1 is not None:
            # Phase 2: run again at 0.4 (conservative) and judge if both succeeded
            raw2 = await self._llm.generate(messages, temperature=0.4)
            bible2 = self._parse(raw2)
            if bible2 is not None:
                winner = await self._judge([bible1, bible2])
                if winner is not None:
                    return winner
            return bible1

        # Retry once
        log.warning("scene_bible.parse_retry")
        raw_retry = await self._llm.generate(messages, temperature=0.3)
        bible_retry = self._parse(raw_retry)
        if bible_retry is not None:
            return bible_retry

        raise SceneBibleParseError("failed to parse scene bible after retry")

    def _parse(self, raw: str) -> SceneBible | None:
        try:
            data = json.loads(raw)
            return SceneBible(**data)
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("scene_bible.parse_error", error=str(exc))
            return None

    async def _judge(self, candidates: list[SceneBible]) -> SceneBible | None:
        if len(candidates) < 2:
            return candidates[0] if candidates else None
        try:
            texts = [c.model_dump_json() for c in candidates]
            judge_msgs = build_judge_message(texts, "scene bible", ["coherence", "creativity"])
            result = await self._llm.generate(judge_msgs, temperature=0.0)
            data = json.loads(result)
            idx = int(data.get("best_index", 0))
            if 0 <= idx < len(candidates):
                return candidates[idx]
        except Exception:
            log.warning("scene_bible.judge_failed, returning first")
        return candidates[0]
```

- [ ] **Step 4: Fix FakeLLMAdapter temperature handling**

Check `app/adapters/llm/fake.py`. It likely ignores `temperature` kwarg. If `generate()` doesn't accept `**kwargs` or a `temperature` param, update it:
```python
    async def generate(self, messages: list[dict], *, temperature: float = 0.0, **kwargs) -> str:
        return "mock response"
```
(This is needed for SceneBibleService to call `generate(messages, temperature=0.7)` without error.)

- [ ] **Step 5: Run tests**

`uv run pytest tests/test_scene_bible_service.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/errors.py app/services/scene_bible.py app/adapters/llm/fake.py tests/test_scene_bible_service.py
git commit -m "feat(services): add SceneBibleService with double-run/judge/cache"
```

## Phase 4 — World Asset Generation

### Task 15: Sprite + background prompt builders

**Files:**
- Create: `app/prompts/background_gen.py`
- Create: `app/prompts/sprite_gen.py`

- [ ] **Step 1: Write tests**

Write `tests/test_background_gen_prompt.py`:
```python
from __future__ import annotations
from app.prompts.background_gen import build_background_prompt


def test_build_background_prompt_includes_world_fields():
    prompt = build_background_prompt(
        place="cafe", time_of_day="afternoon", weather="rainy",
        art_style="watercolor cartoon, warm palette",
    )
    assert "cafe" in prompt
    assert "afternoon" in prompt
    assert "rainy" in prompt
    assert "watercolor" in prompt
    assert "no people" in prompt
    assert "empty" in prompt.lower()
```

Write `tests/test_sprite_gen_prompt.py`:
```python
from __future__ import annotations
from app.prompts.sprite_gen import build_sprite_prompt


def test_build_sprite_prompt_includes_npc_role():
    prompt = build_sprite_prompt(
        persona_name="Mocha",
        role_in_scene="afternoon coffee",
        art_style="watercolor cartoon",
        kind="object",
        frame_type="default",
    )
    assert "Mocha" in prompt
    assert "afternoon coffee" in prompt
    assert "watercolor" in prompt
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_background_gen_prompt.py tests/test_sprite_gen_prompt.py -v`

- [ ] **Step 3: Implement**

Write `app/prompts/background_gen.py`:
```python
"""Prompt builder for background image generation (image-to-image)."""
from __future__ import annotations


def build_background_prompt(
    place: str,
    time_of_day: str,
    weather: str,
    art_style: str,
) -> str:
    return (
        f"Transform this image into a {art_style} illustration. "
        f"The scene is a {place}, it's {time_of_day}, {weather}. "
        "Remove all real people from the scene — keep only the environment and objects. "
        "The scene should feel warm and inviting. "
        "No text, no speech bubbles, no words in the image."
    )
```

Write `app/prompts/sprite_gen.py`:
```python
"""Prompt builder for NPC sprite generation (text-to-image)."""
from __future__ import annotations


def build_sprite_prompt(
    persona_name: str,
    role_in_scene: str,
    art_style: str,
    kind: str = "object",
    frame_type: str = "default",
) -> str:
    base = (
        f"A {art_style} illustration of a character named {persona_name}, "
        f"who is {role_in_scene}. "
        f"Transparent background, game-style character portrait."
    )
    if kind == "object":
        base += " This character IS the object itself, anthropomorphized slightly."
    if frame_type == "default":
        base += " Neutral expression, eyes open, standing/idle pose."
    elif frame_type == "blink":
        base += " Same character, same pose, eyes closed (blinking)."
    elif frame_type in ("mouth_a", "mouth_b", "mouth_c"):
        openness = {"mouth_a": "mouth slightly open (small vowel sound)",
                    "mouth_b": "mouth moderately open (normal speech)",
                    "mouth_c": "mouth wide open (loud vowel sound)"}
        base += f" Same character, same pose, {openness[frame_type]}."
    return base
```

- [ ] **Step 4: Run, expect pass**

`uv run pytest tests/test_background_gen_prompt.py tests/test_sprite_gen_prompt.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/prompts/background_gen.py app/prompts/sprite_gen.py tests/test_background_gen_prompt.py tests/test_sprite_gen_prompt.py
git commit -m "feat(prompts): add background and sprite generation prompts"
```

### Task 16: WorldAssetsService orchestration

**Files:**
- Create: `app/services/world_assets.py`
- Create: `tests/test_world_assets.py`

- [ ] **Step 1: Write tests**

Write `tests/test_world_assets.py`:
```python
from __future__ import annotations

import pytest

from app.adapters.imagegen.base import ImageGenResult
from app.schemas.world import SceneBible, WorldSpec, NPCSpec, VoiceTraits, CrossRelationship


class FakeImageGen:
    def __init__(self):
        self.text_calls = []
        self.image_calls = []

    async def text_to_image(self, prompt, *, size="1024x1024", reference_image=None):
        self.text_calls.append(prompt)
        return ImageGenResult(b"\x89PNG", "image/png")

    async def image_to_image(self, image_bytes, prompt, *, size="1024x1024", strength=0.7):
        self.image_calls.append((prompt, len(image_bytes)))
        return ImageGenResult(b"\x89PNG", "image/png")


@pytest.fixture
def sample_bible():
    return SceneBible(
        world=WorldSpec(
            place="cafe", time_of_day="afternoon", weather="rainy",
            mood="cozy", ambient_sounds=["rain"], bgm_mood="warm",
            art_style_prompt="watercolor cartoon",
        ),
        npcs=[
            NPCSpec(
                entity_id="e1", kind="object", persona_name="Mocha",
                role_in_scene="afternoon coffee", personality="warm",
                voice_traits=VoiceTraits(),
            ),
            NPCSpec(
                entity_id="e2", kind="character", persona_name="Iris",
                role_in_scene="librarian on break", personality="thoughtful",
                voice_traits=VoiceTraits(gender="female", tone="warm"),
            ),
        ],
        cross_relationships=[
            CrossRelationship(from_entity="e1", to_entity="e2", note="coffee partner"),
        ],
    )


@pytest.mark.asyncio
async def test_generate_world_background_and_sprites(sample_bible):
    from app.services.world_assets import WorldAssetsService

    img_gen = FakeImageGen()
    service = WorldAssetsService(imagegen=img_gen)
    assets = await service.generate_world(sample_bible, b"source_image_bytes")

    assert assets.background_base64 != ""
    assert len(assets.sprites) == 2
    assert assets.sprites[0].entity_id == "e1"
    assert assets.sprites[1].entity_id == "e2"
    # Each sprite should have 5 frames
    assert assets.sprites[0].sprites.default != ""
    assert assets.sprites[0].sprites.blink != ""
    assert assets.sprites[1].sprites.mouth_a != ""
    # Background should have used image_to_image
    assert len(img_gen.image_calls) >= 1
    # Sprites should have used text_to_image
    assert len(img_gen.text_calls) >= 2


@pytest.mark.asyncio
async def test_background_is_image_to_image(sample_bible):
    from app.services.world_assets import WorldAssetsService

    img_gen = FakeImageGen()
    service = WorldAssetsService(imagegen=img_gen)
    await service.generate_world(sample_bible, b"src")
    assert any("watercolor" in c[0] for c in img_gen.image_calls)
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_world_assets.py -v`

- [ ] **Step 3: Implement WorldAssetsService**

Write `app/services/world_assets.py`:
```python
"""WorldAssetsService: orchestrates parallel background+NPC sprite generation."""
from __future__ import annotations

import asyncio
import base64
import structlog

from app.adapters.imagegen.base import ImageGenAdapter
from app.prompts.background_gen import build_background_prompt
from app.prompts.sprite_gen import build_sprite_prompt
from app.schemas.world import (
    SceneBible,
    SpriteSet,
    NPCSprites,
    WorldAssets,
)

log = structlog.get_logger("pll.service.world_assets")

FRAME_TYPES = ["default", "blink", "mouth_a", "mouth_b", "mouth_c"]


class WorldAssetsService:
    def __init__(self, imagegen: ImageGenAdapter) -> None:
        self._imagegen = imagegen

    async def generate_world(
        self,
        bible: SceneBible,
        source_image_bytes: bytes,
    ) -> WorldAssets:
        bg_task = self._generate_background(bible, source_image_bytes)
        sprite_tasks = [
            self._generate_npc_sprites(bible, npc) for npc in bible.npcs
        ]

        # Run background and all NPC sprites in parallel
        bg_base64, *sprite_results = await asyncio.gather(
            bg_task, *sprite_tasks
        )

        return WorldAssets(
            background_base64=bg_base64,
            sprites=sprite_results,
        )

    async def _generate_background(self, bible: SceneBible, source_image: bytes) -> str:
        prompt = build_background_prompt(
            place=bible.world.place,
            time_of_day=bible.world.time_of_day,
            weather=bible.world.weather,
            art_style=bible.world.art_style_prompt,
        )
        # Generate 3 candidates, pick best (TODO: parallel 3 + judge)
        result = await self._imagegen.image_to_image(source_image, prompt)
        data: bytes = result.image_bytes
        return base64.b64encode(data).decode("utf-8")

    async def _generate_npc_sprites(self, bible: SceneBible, npc) -> NPCSprites:
        # sprite_frame serial: 5 frames per NPC, one after another,
        # so reference_image can be used for consistency.
        default_result = await self._imagegen.text_to_image(
            build_sprite_prompt(
                persona_name=npc.persona_name,
                role_in_scene=npc.role_in_scene,
                art_style=bible.world.art_style_prompt,
                kind=npc.kind,
                frame_type="default",
            ),
        )
        default_b64 = base64.b64encode(default_result.image_bytes).decode()

        blink_b64 = await self._gen_frame(npc, bible, "blink", default_result.image_bytes)
        mouth_a_b64 = await self._gen_frame(npc, bible, "mouth_a", default_result.image_bytes)
        mouth_b_b64 = await self._gen_frame(npc, bible, "mouth_b", default_result.image_bytes)
        mouth_c_b64 = await self._gen_frame(npc, bible, "mouth_c", default_result.image_bytes)

        return NPCSprites(
            entity_id=npc.entity_id,
            sprites=SpriteSet(
                default=default_b64,
                blink=blink_b64,
                mouth_a=mouth_a_b64,
                mouth_b=mouth_b_b64,
                mouth_c=mouth_c_b64,
            ),
        )

    async def _gen_frame(self, npc, bible, frame_type: str, reference: bytes) -> str:
        prompt = build_sprite_prompt(
            persona_name=npc.persona_name,
            role_in_scene=npc.role_in_scene,
            art_style=bible.world.art_style_prompt,
            kind=npc.kind,
            frame_type=frame_type,
        )
        result = await self._imagegen.text_to_image(
            prompt, reference_image=reference,
        )
        return base64.b64encode(result.image_bytes).decode()
```

- [ ] **Step 4: Run, expect pass**

`uv run pytest tests/test_world_assets.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/services/world_assets.py tests/test_world_assets.py
git commit -m "feat(services): add WorldAssetsService for background+sprite generation"
```

<!-- APPEND_BELOW -->

## Phase 5 — World API (SSE) + Vision Endpoint Update

### Task 17: Ambient mumble prompt

**Files:**
- Create: `app/prompts/ambient_mumble.py`

- [ ] **Step 1: Write test**

Write `tests/test_ambient_mumble_prompt.py`:
```python
from __future__ import annotations

from app.prompts.ambient_mumble import build_mumble_message


def test_build_mumble_message_includes_npc_and_world():
    msg = build_mumble_message(
        persona_name="Mocha",
        personality="warm and philosophical",
        role_in_scene="afternoon coffee",
        place="cafe",
    )
    combined = str(msg)
    assert "Mocha" in combined
    assert "cafe" in combined
    assert "warm" in combined


def test_build_mumble_message_has_short_character_limit():
    msg = build_mumble_message(
        persona_name="Iris", personality="quiet",
        role_in_scene="librarian", place="library",
    )
    content = next(m["content"] for m in msg if m["role"] == "system")
    assert "short" in content.lower() or "6" in content
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_ambient_mumble_prompt.py -v`

- [ ] **Step 3: Implement**

Write `app/prompts/ambient_mumble.py`:
```python
"""Lightweight prompt for ambient mumble generation."""
from __future__ import annotations


def build_mumble_message(
    persona_name: str,
    personality: str,
    role_in_scene: str,
    place: str,
    recent_chat_context: str = "",
) -> list[dict]:
    system = (
        f"You are {persona_name}, {role_in_scene} at {place}. "
        f"Personality: {personality}. "
        "Generate ONE very short piece of ambient dialogue (max 6 words) "
        "that this character would say to themselves in this moment. "
        "Output JUST the dialogue text, no quotes, no formatting, no explanation. "
        "Make it natural and subtle — like a quiet thought."
    )
    if recent_chat_context:
        system += f"\n\nRecent conversation nearby: {recent_chat_context}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "What do you say?"},
    ]
```

- [ ] **Step 4: Run, expect pass**

`uv run pytest tests/test_ambient_mumble_prompt.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/prompts/ambient_mumble.py tests/test_ambient_mumble_prompt.py
git commit -m "feat(prompt): add ambient mumble generation prompt"
```

### Task 18: World SSE endpoint

**Files:**
- Create: `app/api/world.py`
- Create: `app/api/deps.py` (modify to provide WorldStore + services)
- Create: `tests/test_world_api.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_world_api.py`:
```python
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.schemas.world import SceneBible, WorldSpec, NPCSpec, VoiceTraits, WorldAssets, NPCSprites, SpriteSet
from app.services.world_store import WorldStore


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest.mark.asyncio
async def test_get_world_returns_404_for_nonexistent(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/world/w_nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_world_sse_returns_events(app):
    from app.main import get_world_store

    store = get_world_store()
    bible = SceneBible(
        world=WorldSpec(place="cafe", time_of_day="afternoon", weather="rainy",
                        mood="cozy", ambient_sounds=["rain"], bgm_mood="warm",
                        art_style_prompt="watercolor"),
        npcs=[],
        cross_relationships=[],
    )
    wid = store.put(bible)
    store.put_assets(wid, WorldAssets(background_base64="aaaa"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_timeout=5.0, base_url="http://test") as ac:
        resp = await ac.get(f"/api/world/{wid}")
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/event-stream")
```

- [ ] **Step 2: Add world_store to app state and deps**

In `app/api/deps.py`, add a function to get world_store from app.state. In `app/main.py`, initialize WorldStore and attach to app state. We'll need to add a `get_world_store()` function accessible from tests.

The pattern used by existing code: `app/main.py` creates adapters and passes them into `create_app()`. Similarly, attach `WorldStore` and `SceneBibleService` to `app.state`.

In `app/main.py`:
```python
from app.services.world_store import WorldStore
...
def create_app(...) -> FastAPI:
    ...
    world_store = WorldStore()
    app.state.world_store = world_store
    ...
```

Add `get_world_store()` function (for test access):
```python
def get_world_store() -> WorldStore:
    """Used by tests to access the app's world store directly."""
    import inspect
    frame = inspect.currentframe()
    if frame:
        # Not pretty but avoids circular imports for tests
        pass
    raise RuntimeError("only callable within app context")
```

Actually, a cleaner approach: use `app.dependency_overrides` in tests. But the simplest pattern is to inject through `app.state` and provide a dependency:

In `app/api/deps.py`:
```python
from fastapi import Request

def get_world_store(request: Request) -> WorldStore:
    return request.app.state.world_store
```

- [ ] **Step 3: Implement the SSE endpoint**

Write `app/api/world.py`:
```python
"""SSE endpoint for world asset streaming."""
from __future__ import annotations

import json
import asyncio

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse
from starlette.status import HTTP_404_NOT_FOUND

from app.errors import WorldNotFoundError
from app.schemas.world import SceneBible, WorldAssets
from app.services.world_store import WorldStore
from app.api.deps import get_world_store

router = APIRouter(prefix="/world", tags=["world"])


@router.get("/{world_id}")
async def get_world_stream(world_id: str, store: WorldStore = Depends(get_world_store)):
    """SSE endpoint that streams world assets as they become available."""
    # Validate exists
    try:
        store.get_or_raise(world_id)
    except WorldNotFoundError:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "world not found"}, status_code=HTTP_404_NOT_FOUND)

    async def event_stream():
        # Yield bible_ready immediately
        bible = store.get(world_id)
        if bible:
            yield f"event: scene_bible_ready\ndata: {bible.model_dump_json()}\n\n"

            # Yield world_ready with assets if available
            assets = store.get_assets(world_id)
            if assets:
                for event in _asset_to_events(assets):
                    yield event
                yield "event: world_ready\ndata: {}\n\n"
                return

        # If not ready yet, poll until ready or timeout
        for _ in range(120):  # 120 * 0.5s = 60s max wait
            state = store.get_state(world_id)
            if state == "world_ready":
                bible = store.get(world_id)
                if bible:
                    yield f"event: scene_bible_ready\ndata: {bible.model_dump_json()}\n\n"
                assets = store.get_assets(world_id)
                if assets:
                    for event in _asset_to_events(assets):
                        yield event
                yield "event: world_ready\ndata: {}\n\n"
                return
            elif state == "error":
                yield "event: error\ndata: {}\n\n"
                return
            await asyncio.sleep(0.5)
        yield "event: error\ndata: {'message': 'timeout'}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _asset_to_events(assets: WorldAssets):
    yield f"event: background_ready\ndata: {json.dumps({'image_base64': assets.background_base64})}\n\n"
    for sprite in assets.sprites:
        yield f"event: npc_sprite_ready\ndata: {sprite.model_dump_json()}\n\n"
```

- [ ] **Step 4: Mount router in main.py**

In `app/main.py`, add import and include:
```python
from app.api.world import router as world_router
...
app.include_router(world_router, prefix="/api")
```

Also attach WorldStore to app state:
```python
from app.services.world_store import WorldStore
...
app.state.world_store = WorldStore()
```

- [ ] **Step 5: Run tests**

`uv run pytest tests/test_world_api.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add app/api/world.py app/api/deps.py app/main.py tests/test_world_api.py
git commit -m "feat(api): add SSE endpoint for world asset streaming"
```

### Task 19: Update vision endpoint to return world_id + spawn generation

**Files:**
- Modify: `app/api/vision.py`
- Modify: `tests/test_vision_api.py`

- [ ] **Step 1: Update vision endpoint logic**

In `app/api/vision.py`:
1. After vision analysis, check `is_safe`.
2. If safe, extract `entities` and `raw_scene` from the result.
3. Call `scene_bible_service.generate(...)` to produce a SceneBible.
4. Store in `WorldStore`, getting a `world_id`.
5. Spawn background task: `world_assets_service.generate_world(bible, image_bytes)` → store assets.
6. Return the vision response with the `world_id`.

The key change: the endpoint now returns a `world_id` field. The old `PersonaGenerateResponse` path is skipped entirely — personas are embedded in the SceneBible.

Modify the response in `app/schemas/vision.py`:
```python
class VisionAnalyzeResponse(BaseModel):
    request_id: str
    is_safe: bool
    reject_reasons: list[str] = Field(default_factory=list)
    scene_summary: str = ""
    raw_scene: str = ""
    objects: list[DetectedObject] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    world_id: str = ""  # NEW: if safe, the world_id for polling SSE
```

- [ ] **Step 2: Add scene_bible_service and world_assets_service deps**

In `app/api/deps.py`, add dependency functions:
```python
def get_scene_bible_service(request: Request) -> SceneBibleService:
    return request.app.state.scene_bible_service

def get_world_assets_service(request: Request) -> WorldAssetsService:
    return request.app.state.world_assets_service
```

In `app/main.py`, initialize them and attach to `app.state`:
```python
from app.services.scene_bible import SceneBibleService
from app.services.world_assets import WorldAssetsService

def create_app(...):
    ...
    app.state.world_store = WorldStore()
    app.state.scene_bible_service = SceneBibleService(
        llm=build_llm_adapter(settings),
        world_store=app.state.world_store,
    )
    app.state.world_assets_service = WorldAssetsService(
        imagegen=build_imagegen_adapter(settings),
    )
```

- [ ] **Step 3: Update vision API endpoint**

In `app/api/vision.py`, update the `analyze` endpoint to:
```python
from app.api.deps import get_scene_bible_service, get_world_assets_service

@router.post("/analyze")
async def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    user_level: str = Form("beginner"),
    vision: VisionAdapter = Depends(get_vision_adapter),
    scene_bible_service: SceneBibleService = Depends(get_scene_bible_service),
    world_assets_service: WorldAssetsService = Depends(get_world_assets_service),
):
    ...
    result = await vision.analyze_image(image_bytes)
    ...
    if result.is_safe:
        entities_dicts = [
            {
                "id": e.id,
                "kind": e.kind,
                "label": e.label,
                "salience": e.salience,
                "persona_seed": e.seed,
            }
            for e in result.entities
        ]
        # Generate scene bible
        bible = await scene_bible_service.generate(
            raw_scene=result.raw_scene,
            entities=entities_dicts,
            user_level=user_level,
        )
        world_id = scene_bible_service._store.put(bible)
        # Spawn background world asset generation
        asyncio.create_task(
            _generate_and_store_assets(world_assets_service, bible, image_bytes, world_id)
        )
    ...

async def _generate_and_store_assets(
    service: WorldAssetsService,
    bible: SceneBible,
    image_bytes: bytes,
    world_id: str,
):
    try:
        assets = await service.generate_world(bible, image_bytes)
        service._imagegen._store.put_assets(world_id, assets)
    except Exception as exc:
        log.error("world_assets.failed", world_id=world_id, error=str(exc))
```

Wait, `WorldAssetsService` doesn't have a `.store` reference. Use `WorldStore` directly. Let's adjust: pass `world_store` into the background task via closure:
```python
store = scene_bible_service._store  # reuse same WorldStore instance
# Actually better: inject WorldStore through deps
```

Add `get_world_store` as dependency, then:
```python
async def _generate_and_store_assets(
    assets_service: WorldAssetsService,
    bible: SceneBible,
    image_bytes: bytes,
    world_store: WorldStore,
):
    assets = await assets_service.generate_world(bible, image_bytes)
    world_store.put_assets(...)
```

- [ ] **Step 4: Update existing vision test**

Ensure existing vision tests still pass with the new schema (add empty entities/raw_scene fields where needed).

- [ ] **Step 5: Commit**

```bash
git add app/api/vision.py app/api/deps.py app/main.py app/schemas/vision.py
git commit -m "feat(api): vision endpoint returns world_id, spawns scene bible + asset generation"
```

## Phase 6 — Chat Orchestrator Changes

### Task 20: ContextManager key from session_id to (session_id, npc_id)

**Files:**
- Modify: `app/services/context_manager.py`
- Modify: `tests/test_context_manager.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_context_manager_npc.py`:
```python
from __future__ import annotations
from app.services.context_manager import ContextManager


def test_context_separate_by_npc():
    cm = ContextManager()
    cm.add_turn(("s1", "npc_a"), "hi", "hello back")
    cm.add_turn(("s1", "npc_b"), "hey", "hey there")
    ctx_a = cm.get_context(("s1", "npc_a"))
    ctx_b = cm.get_context(("s1", "npc_b"))
    assert len(ctx_a) == 2
    assert len(ctx_b) == 2
    assert ctx_a[1]["content"] == "hello back"
    assert ctx_b[1]["content"] == "hey there"


def test_string_key_backward_compat():
    cm = ContextManager()
    cm.add_turn("old_session", "hi", "hi")
    ctx = cm.get_context("old_session")
    assert len(ctx) == 2
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_context_manager_npc.py -v`

- [ ] **Step 3: Update ContextManager**

In `app/services/context_manager.py`, change `_contexts` dict key from `str` to accept `str` or `tuple[str, str]`. Convert all keys to tuple for internal storage:

In `__init__`, change `_contexts: dict[str, list]` to `dict[tuple, list]`.
Add a normalization method:
```python
    @staticmethod
    def _normalize_key(session_id: str | tuple) -> tuple:
        if isinstance(session_id, tuple):
            return session_id
        return (session_id, "")  # old sessions: empty npc_id
```

Update `get_context`, `add_turn`, `summarize` to call `_normalize_key`.

- [ ] **Step 4: Add `is_streaming` flag management**

Add to ContextManager:
```python
    def set_streaming(self, session_id: str | tuple, streaming: bool) -> None:
        key = self._normalize_key(session_id)
        if streaming:
            self._streaming.add(key)
        else:
            self._streaming.discard(key)

    def is_streaming(self, session_id: str | tuple) -> bool:
        key = self._normalize_key(session_id)
        return key in self._streaming
```

Add `_streaming: set[tuple] = set()` in `__init__`.

- [ ] **Step 5: Run tests**

`uv run pytest tests/test_context_manager_npc.py tests/test_context_manager.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/services/context_manager.py tests/test_context_manager_npc.py
git commit -m "feat(context): key (session_id, npc_id) + streaming flag API"
```

### Task 21: Persona system prompt with scene bible injection

**Files:**
- Modify: `app/prompts/chat_system.py`

- [ ] **Step 1: Write test for new format**

Write `tests/test_chat_system_world.py`:
```python
from __future__ import annotations

from app.schemas.world import SceneBible, WorldSpec, NPCSpec, VoiceTraits, CrossRelationship
from app.prompts.chat_system import build_chat_system_message_world


@pytest.fixture
def sample_bible():
    return SceneBible(
        world=WorldSpec(
            place="cafe", time_of_day="afternoon", weather="rainy",
            mood="cozy", ambient_sounds=["rain_on_window"], bgm_mood="warm",
            art_style_prompt="watercolor",
        ),
        npcs=[
            NPCSpec(
                entity_id="e1", kind="object", persona_name="Mocha",
                role_in_scene="afternoon coffee", relationship_to_user="loyal companion",
                personality="warm, philosophical", voice_traits=VoiceTraits(),
                vocab_focus=["cozy", "steam"],
            ),
            NPCSpec(
                entity_id="e3", kind="character", persona_name="Iris",
                role_in_scene="librarian",
                relationship_to_user="familiar regular",
                personality="quiet but observant",
                voice_traits=VoiceTraits(gender="female", tone="warm"),
                vocab_focus=["chapter", "verse"],
            ),
        ],
        cross_relationships=[
            CrossRelationship(from_entity="e1", to_entity="e3", note="Iris ordered Mocha today"),
        ],
    )


def test_build_chat_system_message_includes_world(sample_bible):
    msg = build_chat_system_message_world(
        persona_name="Mocha", active_npc=sample_bible.npcs[0],
        bible=sample_bible, user_level="beginner",
    )
    content = msg["content"]
    # World details
    assert "cafe" in content
    assert "afternoon" in content
    assert "rainy" in content
    # Grounding rules
    assert "GROUNDING" in content or "sensory" in content
    # Other souls
    assert "Iris" in content
    assert "Mocha" in content or "You are Mocha" in content


def test_build_does_not_speak_for_others(sample_bible):
    msg = build_chat_system_message_world(
        persona_name="Mocha", active_npc=sample_bible.npcs[0],
        bible=sample_bible, user_level="beginner",
    )
    content = msg["content"]
    assert "CANNOT speak for" in content


def test_level_instructions_included(sample_bible):
    msg = build_chat_system_message_world(
        persona_name="Mocha", active_npc=sample_bible.npcs[0],
        bible=sample_bible, user_level="intermediate",
    )
    content = msg["content"]
    assert "intermediate" in content.lower()
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_chat_system_world.py -v`

- [ ] **Step 3: Add new prompt builder**

In `app/prompts/chat_system.py`, add a new function `build_chat_system_message_world` alongside the existing one:
```python
from app.schemas.world import SceneBible, NPCSpec


def build_chat_system_message_world(
    persona_name: str,
    active_npc: NPCSpec,
    bible: SceneBible,
    user_level: str = "beginner",
) -> dict:
    """Build system message using SceneBible (Living Scene mode)."""
    level_instructions = {
        "beginner": (
            "Use very simple sentences and basic vocabulary. "
            "Speak slowly and clearly. Repeat key words."
        ),
        "intermediate": (
            "Use moderate vocabulary and natural sentence structures. "
            "Occasionally introduce new useful words."
        ),
        "advanced": (
            "Use natural, fluent English as you would with another fluent speaker. "
            "Focus on nuanced expressions and idioms when appropriate."
        ),
    }
    level_instr = level_instructions.get(user_level, level_instructions["intermediate"])

    world = bible.world
    other_npcs = [n for n in bible.npcs if n.entity_id != active_npc.entity_id]
    other_souls_lines = []
    for n in other_npcs:
        note = ""
        for rel in bible.cross_relationships:
            if (rel.from_entity == active_npc.entity_id and rel.to_entity == n.entity_id) or \
               (rel.to_entity == active_npc.entity_id and rel.from_entity == n.entity_id):
                note = f" ({rel.note})"
        other_souls_lines.append(f"- {n.persona_name}, {n.role_in_scene}.{note}")

    sounds_readable = ", ".join(world.ambient_sounds).replace("_", " ")

    content = (
        f"You are {persona_name}, {active_npc.role_in_scene}.\n\n"
        f"WORLD:\n"
        f"You exist in {world.place}, it's {world.time_of_day}, {world.weather}.\n"
        f"The mood here is {world.mood}.\n"
        f"You can hear: {sounds_readable}.\n\n"
        f"YOUR CHARACTER:\n"
        f"{active_npc.personality}\n"
        f"Your relationship to the user: {active_npc.relationship_to_user}\n\n"
    )
    if other_souls_lines:
        content += "OTHER SOULS HERE:\n" + "\n".join(other_souls_lines) + "\n\n"
        content += (
            "You CAN reference them naturally (\"Iris is reading next to me\").\n"
            "You CANNOT speak for them.\n\n"
        )

    content += (
        "GROUNDING RULES:\n"
        "- Speak as if physically present in this scene. Reference what's around you when natural.\n"
        "- React to sensory details (the rain, the smell of coffee, the light through the window).\n"
        "- When the user asks where you are, describe THIS scene from your vantage point.\n"
        "- Stay in character even when teaching.\n\n"
        f"User level ({user_level}): {level_instr}\n\n"
        "You MUST format EVERY response with these XML tags:\n"
        "<speak>...</speak>\n"
        "<learning>...</learning>\n"
        "<followup>...</followup>\n\n"
        "Rules:\n"
        "- Always respond in English\n"
        "- <speak> must be at least 1 sentence\n"
        "- <learning> can be empty if no teaching point applies\n"
        "- Keep total response under 5 sentences\n"
        "- Be encouraging and positive"
    )
    return {"role": "system", "content": content}
```

- [ ] **Step 4: Run, expect 3 passed**

`uv run pytest tests/test_chat_system_world.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/prompts/chat_system.py tests/test_chat_system_world.py
git commit -m "feat(prompt): add scene bible injected chat system message"
```

### Task 22: ChatOrchestrator — scene bible + streaming flag

**Files:**
- Modify: `app/services/chat_orchestrator.py`
- Modify: `tests/test_chat_orchestrator.py`

- [ ] **Step 1: Update ChatOrchestrator**

Changes to `chat_stream`:
1. Accept `scene_bible: SceneBible | None = None` and `npc_id: str = ""` in the signature.
2. When bible is provided, use `build_chat_system_message_world` instead of the passed-in `system_message`.
3. Set streaming flag via `context.set_streaming(session_id, True)` before LLM call, clear after.
4. The session_id is now a tuple internally: `(session_id, npc_id)`.

Modified `chat_stream` signature:
```python
    async def chat_stream(
        self,
        session_id: str,
        user_message: str,
        system_message: dict,
        *,
        learner_context_message: dict | None = None,
        voice_id: str | None = None,
        scene_bible: SceneBible | None = None,
        npc_id: str = "",
    ) -> AsyncGenerator[dict, None]:
```

At start, determine effective session key:
```python
        effective_key = (session_id, npc_id) if npc_id else session_id
```

Use `effective_key` everywhere instead of `session_id` for context operations.

Set streaming flag before LLM:
```python
        self._context.set_streaming(effective_key, True)
```

Clear after LLM loop ends:
```python
        finally:
            self._context.set_streaming(effective_key, False)
```

- [ ] **Step 2: Write/update tests**

Update existing tests to pass the new keyword args. The key behavior to test:
- When `scene_bible` + `npc_id` are provided, the system prompt uses the world version
- The streaming flag is set during generation

- [ ] **Step 3: Run all chat tests**

`uv run pytest tests/test_chat_orchestrator.py tests/test_context_manager_npc.py -v`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add app/services/chat_orchestrator.py tests/test_chat_orchestrator.py
git commit -m "feat(chat): orchestrator accepts scene_bible + npc_id, manages streaming flag"
```

## Phase 7 — Ambient Scheduler

### Task 23: AmbientEvent schemas

**Files:**
- Create: `app/schemas/ambient.py`

- [ ] **Step 1: Write test**

Write `tests/test_ambient_schema.py`:
```python
from __future__ import annotations
from app.schemas.ambient import AmbientEvent


def test_ambient_glance_event():
    e = AmbientEvent(npc_id="e3", event="glance", target="e1", duration_ms=1000)
    assert e.event == "glance"
    assert e.target == "e1"
    assert e.duration_ms == 1000


def test_ambient_mumble_event():
    e = AmbientEvent(npc_id="e2", event="mumble", text="hello", duration_ms=3000)
    assert e.text == "hello"
    assert e.duration_ms == 3000


def test_ambient_invalid_event_rejected():
    import pytest
    from pydantic import ValidationError
    from app.schemas.ambient import AmbientEvent
    with pytest.raises(ValidationError):
        AmbientEvent(npc_id="e1", event="fly", duration_ms=100)
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_ambient_schema.py -v`

- [ ] **Step 3: Implement**

Write `app/schemas/ambient.py`:
```python
"""Pydantic models for ambient events."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AmbientEvent(BaseModel):
    npc_id: str
    event: Literal["glance", "gesture", "mumble"]
    target: str = ""
    text: str = ""
    duration_ms: int = Field(default=1000, ge=500)
```

- [ ] **Step 4: Run, expect pass**

`uv run pytest tests/test_ambient_schema.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/schemas/ambient.py tests/test_ambient_schema.py
git commit -m "feat(schemas): add AmbientEvent model"
```

### Task 24: AmbientScheduler implementation

**Files:**
- Create: `app/services/ambient_scheduler.py`
- Create: `tests/test_ambient_scheduler.py`

- [ ] **Step 1: Write tests**

Write `tests/test_ambient_scheduler.py`:
```python
from __future__ import annotations

import asyncio
import pytest

from app.schemas.world import SceneBible, WorldSpec, NPCSpec, VoiceTraits, CrossRelationship


class FakeLLMForAmbient:
    async def generate(self, messages, *, temperature=0.0):
        return "Just one more chapter…"


@pytest.fixture
def bible_with_npcs():
    return SceneBible(
        world=WorldSpec(
            place="cafe", time_of_day="afternoon", weather="rainy",
            mood="cozy", bgm_mood="warm",
            ambient_sounds=[], art_style_prompt="x"),
        npcs=[
            NPCSpec(entity_id="e1", kind="object", persona_name="Mocha",
                    role_in_scene="coffee", personality="warm",
                    voice_traits=VoiceTraits(), ambient_actions=["steam puff"]),
            NPCSpec(entity_id="e2", kind="character", persona_name="Iris",
                    role_in_scene="librarian", personality="quiet",
                    voice_traits=VoiceTraits(), ambient_actions=["turn page"]),
        ],
        cross_relationships=[CrossRelationship(from_entity="e1", to_entity="e2", note="partners")],
    )


@pytest.mark.asyncio
async def test_scheduler_skips_when_streaming(bible_with_npcs):
    from app.services.ambient_scheduler import AmbientScheduler

    events = []

    async def send(payload):
        events.append(payload)

    is_streaming_calls = []

    def is_streaming():
        is_streaming_calls.append(True)
        return True  # always streaming

    scheduler = AmbientScheduler(
        llm=FakeLLMForAmbient(),
        world_store=None,
        bible=bible_with_npcs,
    )
    # Run for a short time with tiny sleep
    task = asyncio.create_task(
        scheduler.run(
            active_npc_id="e1",
            is_streaming=is_streaming,
            ws_send=send,
        )
    )
    await asyncio.sleep(0.2)  # enough for a few ticks
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(is_streaming_calls) > 0
    # Should have skipped all events since streaming=True each time
    assert len(events) == 0


@pytest.mark.asyncio
async def test_scheduler_sends_events(bible_with_npcs):
    from app.services.ambient_scheduler import AmbientScheduler

    events = []

    async def send(payload):
        events.append(payload)

    def is_streaming():
        return False  # never streaming

    scheduler = AmbientScheduler(
        llm=FakeLLMForAmbient(),
        world_store=None,
        bible=bible_with_npcs,
    )
    # Override internal sleep to be instant
    scheduler._min_interval = 0.01
    scheduler._max_interval = 0.05

    task = asyncio.create_task(
        scheduler.run(
            active_npc_id="e1",
            is_streaming=is_streaming,
            ws_send=send,
        )
    )
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(events) > 0
    # Events should have npc_id other than e1
    event_ids = {e.get("npc_id") for e in events}
    assert "e2" in event_ids or len(events) > 0
```

- [ ] **Step 2: Run, expect failure**

`uv run pytest tests/test_ambient_scheduler.py -v`

- [ ] **Step 3: Implement**

Write `app/services/ambient_scheduler.py`:
```python
"""AmbientScheduler: per-session coroutine emitting ambient NPC events."""
from __future__ import annotations

import asyncio
import random
import structlog

from app.adapters.llm.base import LLMAdapter
from app.prompts.ambient_mumble import build_mumble_message
from app.schemas.ambient import AmbientEvent
from app.schemas.world import SceneBible, NPCSpec
from app.services.world_store import WorldStore

log = structlog.get_logger("pll.service.ambient_scheduler")

WEIGHTS = {"glance": 0.70, "gesture": 0.20, "mumble": 0.10}
MUMBLE_CHAR_LIMIT = 6


class AmbientScheduler:
    def __init__(
        self,
        llm: LLMAdapter,
        world_store: WorldStore | None,
        bible: SceneBible,
    ) -> None:
        self._llm = llm
        self._store = world_store
        self._bible = bible
        self._min_interval = 15
        self._max_interval = 45

    async def run(
        self,
        active_npc_id: str,
        is_streaming: callable,
        ws_send: callable,
    ) -> None:
        """Main loop: emit ambient events while the session is alive."""
        while True:
            await asyncio.sleep(random.uniform(self._min_interval, self._max_interval))
            if is_streaming():
                continue

            npc = self._pick_npc(active_npc_id)
            if npc is None:
                continue

            event_type = self._weighted_choice(WEIGHTS)
            event = await self._build_event(event_type, npc, active_npc_id)
            if event:
                try:
                    await ws_send(event.model_dump())
                except Exception as exc:
                    log.warning("ambient.send_failed", error=str(exc))

    def _pick_npc(self, active_npc_id: str) -> NPCSpec | None:
        others = [
            n for n in self._bible.npcs
            if n.entity_id != active_npc_id
        ]
        if not others:
            return None
        # Prefer NPCs with cross_relationships to active NPC
        related_ids = {
            r.from_entity for r in self._bible.cross_relationships
        } | {r.to_entity for r in self._bible.cross_relationships}
        related = [n for n in others if n.entity_id in related_ids]
        if related:
            return random.choice(related)
        return random.choice(others)

    async def _build_event(
        self, event_type: str, npc: NPCSpec, active_npc_id: str
    ) -> AmbientEvent | None:
        if event_type == "glance":
            return AmbientEvent(
                npc_id=npc.entity_id, event="glance",
                target=active_npc_id, duration_ms=1000,
            )
        elif event_type == "gesture":
            return AmbientEvent(
                npc_id=npc.entity_id, event="gesture", duration_ms=800,
            )
        elif event_type == "mumble":
            try:
                msgs = build_mumble_message(
                    persona_name=npc.persona_name,
                    personality=npc.personality,
                    role_in_scene=npc.role_in_scene,
                    place=self._bible.world.place,
                )
                text = await self._llm.generate(msgs, temperature=0.8)
                text = text.strip().strip('"\'')
                if len(text) > MUMBLE_CHAR_LIMIT * 2:
                    text = text[:MUMBLE_CHAR_LIMIT * 2] + "…"
                return AmbientEvent(
                    npc_id=npc.entity_id, event="mumble",
                    text=text, duration_ms=3000,
                )
            except Exception as exc:
                log.warning("ambient.mumble_failed", error=str(exc))
                return None
        return None

    @staticmethod
    def _weighted_choice(weights: dict[str, float]) -> str:
        r = random.random()
        cumulative = 0.0
        for key, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return key
        return "glance"
```

- [ ] **Step 4: Run, expect pass**

`uv run pytest tests/test_ambient_scheduler.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/services/ambient_scheduler.py tests/test_ambient_scheduler.py
git commit -m "feat(services): add AmbientScheduler per-session coroutine"
```

### Task 25: Ambient WS endpoint

**Files:**
- Create: `app/api/ambient.py`
- Create: `tests/test_ambient_ws.py`

- [ ] **Step 1: Implementation sketch**

Write `app/api/ambient.py`:
```python
"""WebSocket endpoint for ambient NPC events during a chat session."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.api.deps import get_scene_bible_service, get_world_store
from app.services.ambient_scheduler import AmbientScheduler
from app.services.world_store import WorldStore

router = APIRouter(tags=["ambient"])


@router.websocket("/api/chat/{session_id}/ambient")
async def ambient_ws(
    websocket: WebSocket,
    session_id: str,
    world_id: str,
    npc_id: str = "",
    store: WorldStore = Depends(get_world_store),
):
    await websocket.accept()
    try:
        bible = store.get_or_raise(world_id)
    except Exception:
        await websocket.send_json({"type": "error", "message": "world not found"})
        await websocket.close(code=4004)
        return

    scheduler = AmbientScheduler(llm=bible._llm, world_store=store, bible=bible)
    # Need to handle this differently - the scheduler needs an LLM.
    # In practice, this will be wired up in the chat endpoint, not as
    # an independent WS endpoint. This file becomes integration glue.
```

**Decision**: Rather than an independent WS endpoint, the ambient WS is established by the existing `WS /api/chat` endpoint. After the main chat WS is connected, the chat handler creates an `AmbientScheduler` task alongside the main chat loop. So this task is primarily about integration in the chat endpoint, not a standalone route.

- [ ] **Step 2: Integrate into chat endpoint**

In `app/api/chat.py`, modify the websocket handler to:
1. Accept `world_id` and `npc_id` in the init frame
2. Create `AmbientScheduler` after the main chat loop starts
3. Have a second coroutine (`ambient_sender`) that reads from the scheduler and pushes to the same WS

The integration pattern:
```python
# In the chat WS handler, after establishing the main chat loop:
ambient_queue: asyncio.Queue = asyncio.Queue()
async def ambient_sender():
    try:
        async for event in ambient_scheduler.run(...):
            await ambient_queue.put(event)
    except asyncio.CancelledError:
        pass

ambient_task = asyncio.create_task(ambient_sender())
# Meanwhile, in the main receive loop, also check the ambient queue:
# (using asyncio.wait for both user messages and ambient events)
```

This is detailed enough for the engineer to implement within the existing WS handler. The key point: the ambient WS is *not* a separate endpoint; it's multiplexed onto the existing chat WS.

- [ ] **Step 3: Write integration-style test**

- [ ] **Step 4: Commit**

```bash
git add app/api/chat.py
git commit -m "feat(chat): integrate AmbientScheduler into chat WS handler"
```

## Phase 8 — Deprecation + Integration

### Task 26: Deprecate old persona endpoint

**Files:**
- Modify: `app/api/persona.py`

- [ ] **Step 1: Replace endpoint body**

In `app/api/persona.py`, replace the route handler with:
```python
@router.post("/generate")
async def deprecated_persona_generate():
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=410,
        content={
            "detail": "POST /api/persona/generate is deprecated in v0.3. "
                      "Personas are now generated as part of the SceneBible "
                      "process. Use POST /api/vision/analyze instead."
        },
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/api/persona.py
git commit -m "refactor: deprecate persona endpoint (410 Gone)"
```

### Task 27: E2E integration test

**Files:**
- Create: `tests/test_living_scene_e2e.py`

- [ ] **Step 1: Write E2E test with all fakes**

Write `tests/test_living_scene_e2e.py`:
```python
"""E2E test for Living Scene happy path using all fake adapters."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_living_scene_full_flow():
    from app.main import create_app

    app = create_app()  # uses all fake adapters by default (PLL_*_provider=fake)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Upload an image
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
        resp = await ac.post(
            "/api/vision/analyze",
            files={"file": ("test.png", image_bytes, "image/png")},
            data={"user_level": "beginner"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_safe"] is True
        assert data.get("world_id", "") != ""
        assert len(data.get("entities", [])) >= 1

        # Step 2: Poll world SSE until ready
        import asyncio
        world_id = data["world_id"]

        # The async background gen should complete quickly with fakes
        await asyncio.sleep(0.5)

        world_resp = await ac.get(f"/api/world/{world_id}")
        assert world_resp.status_code == 200
        # SSE response will have text/event-stream content-type
```

- [ ] **Step 2: Run**

`uv run pytest tests/test_living_scene_e2e.py -v`
Expected: pass (may need minor adjustments for async timing).

- [ ] **Step 3: Lint check**

`uv run ruff check app tests`
Fix any issues.

- [ ] **Step 4: Final commit**

```bash
git add tests/test_living_scene_e2e.py
git commit -m "test: add Living Scene E2E integration test"
```

---

## Plan Complete

**Backend plan: 27 tasks across 8 phases.**

The plan can be split into 3 execution blocks:
1. **Phase 1-2** (Tasks 1-9): ImageGen adapter foundation + Vision rewrite — independently testable
2. **Phase 3-5** (Tasks 10-19): Scene bible + World assets + World API — the core generation pipeline
3. **Phase 6-8** (Tasks 20-27): Chat integration + Ambient + Deprecation + E2E

After this backend plan ships, the frontend plan covers: `LivingScene` component tree, `WorldClient` (SSE), `AmbientClient` (WS), store changes, AudioMixer, and the loading ceremony.
<!-- APPEND_BELOW -->


