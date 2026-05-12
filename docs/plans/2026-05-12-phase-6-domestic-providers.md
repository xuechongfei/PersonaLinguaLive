# Phase 6: Domestic AI Providers (Qwen-VL + DeepSeek + MiniMax)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three domestic AI providers — Qwen-VL-Max (vision), DeepSeek-V4-Flash (LLM), MiniMax speech-02-hd (TTS) — behind the existing adapter layer, so the app runs in mainland China without depending on OpenAI. STT defers to a Whisper-compatible adapter as a follow-up (frontend Web Speech API already covers MVP).

**Architecture:** Each provider gets its own adapter module under `app/adapters/{vision,llm,tts}/`, implementing the existing `Protocol` from `base.py`. `factory.py` gains new branches keyed off the existing `PLL_AI_*_PROVIDER` literal type. OpenAI adapters stay in place as fallback. The persona system gains a voice-selection step that maps personality traits to MiniMax's 300+ English voice IDs.

**Tech Stack:** Python 3.12+, httpx (async), respx (test mocking), pydantic-settings. All three new providers expose OpenAI-compatible Chat-Completions APIs (DeepSeek, Qwen-VL via DashScope compatible-mode), except MiniMax TTS which has its own JSON schema at `https://api.minimaxi.chat/v1/t2a_v2`.

**External references verified 2026-05-12:**
- DeepSeek V4: model `deepseek-v4-flash`, base URL `https://api.deepseek.com/v1`, OpenAI-compatible. Legacy `deepseek-chat` deprecates 2026-07-24.
- Qwen-VL: model `qwen-vl-max-latest`, base URL `https://dashscope.aliyuncs.com/compatible-mode/v1`, OpenAI-compatible.
- MiniMax: endpoint `https://api.minimaxi.chat/v1/t2a_v2` (CN), model `speech-02-hd`, English voice example `English_expressive_narrator`. Auth: `Authorization: Bearer <api_key>` plus mandatory `GroupId` query param.

---

## File Structure

**New files:**
- `app/adapters/llm/deepseek_llm.py` — DeepSeek-V4 adapter (OpenAI-compatible, both `generate` and `generate_stream`)
- `app/adapters/vision/qwen_vision.py` — Qwen-VL-Max adapter (OpenAI-compatible chat completions with image_url parts)
- `app/adapters/tts/minimax_tts.py` — MiniMax T2A adapter (custom JSON schema, returns hex-encoded audio)
- `app/services/voice_picker.py` — maps persona traits → MiniMax voice ID
- `tests/test_deepseek_llm_adapter.py`
- `tests/test_qwen_vision_adapter.py`
- `tests/test_minimax_tts_adapter.py`
- `tests/test_voice_picker.py`

**Modified files:**
- `app/config.py` — extend `ai_*_provider` Literals, add `deepseek_*`, `qwen_*`, `minimax_*` settings
- `app/adapters/factory.py` — add `deepseek` / `qwen` / `minimax` branches
- `app/services/persona_service.py` — emit `voice_id` in response
- `app/schemas/persona.py` — add `voice_id` field
- `app/services/chat_orchestrator.py` — accept `voice_id` arg, pass to TTS
- `app/api/chat.py` — accept `voice_id` from init frame, propagate to orchestrator
- `app/prompts/persona_gen.py` — request `voice_traits` field for voice picker
- `tests/test_llm_factory.py`, `tests/test_vision_factory.py`, `tests/test_tts_factory.py` — cover new branches
- `.env.example` — document new provider variables
- `docs/plans/README.md` — add Phase 6 row
- `docs/prd/2026-05-09-personalingualive-prd.md` — close Open Question #1 in §7.2, log v0.2 in §9
- `README.md` — update provider matrix

---

## Sub-phase 6.1 — Config & dependencies

Widen the provider `Literal`s and add settings for the three new providers. Update the `model_validator` so each provider only requires its own credentials. Update `.env.example`.

**Files:**
- Modify: `app/config.py`
- Modify: `tests/test_config.py`
- Modify: `.env.example`

### Task 6.1.1: Widen Literal + add new settings (failing test)

- [ ] **Step 1: Write the failing test** in `tests/test_config.py` (append at bottom)

```python
def test_deepseek_provider_requires_deepseek_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "deepseek")
    with pytest.raises(ValueError, match="PLL_DEEPSEEK_API_KEY"):
        Settings()


def test_deepseek_provider_loads_with_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("PLL_DEEPSEEK_API_KEY", "sk-test")
    settings = Settings()
    assert settings.ai_llm_provider == "deepseek"
    assert settings.deepseek_api_key.get_secret_value() == "sk-test"
    assert settings.deepseek_base_url == "https://api.deepseek.com/v1"
    assert settings.deepseek_model_llm == "deepseek-v4-flash"


def test_qwen_provider_requires_qwen_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "qwen")
    with pytest.raises(ValueError, match="PLL_QWEN_API_KEY"):
        Settings()


def test_qwen_provider_loads_with_key(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "qwen")
    monkeypatch.setenv("PLL_QWEN_API_KEY", "sk-qwen")
    settings = Settings()
    assert settings.ai_vision_provider == "qwen"
    assert settings.qwen_api_key.get_secret_value() == "sk-qwen"
    assert settings.qwen_base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert settings.qwen_model_vision == "qwen-vl-max-latest"


def test_minimax_provider_requires_key_and_group_id(monkeypatch):
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "minimax")
    with pytest.raises(ValueError, match="PLL_MINIMAX_API_KEY"):
        Settings()
    monkeypatch.setenv("PLL_MINIMAX_API_KEY", "sk-mm")
    with pytest.raises(ValueError, match="PLL_MINIMAX_GROUP_ID"):
        Settings()


def test_minimax_provider_loads_with_key_and_group(monkeypatch):
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "minimax")
    monkeypatch.setenv("PLL_MINIMAX_API_KEY", "sk-mm")
    monkeypatch.setenv("PLL_MINIMAX_GROUP_ID", "grp123")
    settings = Settings()
    assert settings.ai_tts_provider == "minimax"
    assert settings.minimax_api_key.get_secret_value() == "sk-mm"
    assert settings.minimax_group_id == "grp123"
    assert settings.minimax_base_url == "https://api.minimaxi.chat/v1"
    assert settings.minimax_model_tts == "speech-02-hd"
    assert settings.minimax_default_voice == "English_expressive_narrator"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -k "deepseek or qwen or minimax" -v`
Expected: FAIL — `Literal['fake', 'openai']` rejects new values; `deepseek_*`, `qwen_*`, `minimax_*` attributes do not exist.

- [ ] **Step 3: Extend `app/config.py`**

Replace the four `ai_*_provider` Literal lines and add new fields. Final `Settings` body relevant section:

```python
    # === AI 适配层 ===
    ai_vision_provider: Literal["fake", "openai", "qwen"] = "fake"
    ai_llm_provider: Literal["fake", "openai", "deepseek"] = "fake"
    ai_tts_provider: Literal["fake", "openai", "minimax"] = "fake"
    ai_stt_provider: Literal["fake", "openai"] = "fake"

    # OpenAI
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model_vision: str = "gpt-4o"
    openai_model_llm: str = "gpt-4o-mini"
    openai_model_tts: str = "tts-1-hd"
    openai_model_stt: str = "whisper-1"
    openai_tts_voice: str = "alloy"
    openai_request_timeout_s: float = 30.0

    # DeepSeek (LLM, OpenAI-compatible)
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model_llm: str = "deepseek-v4-flash"
    deepseek_request_timeout_s: float = 30.0

    # Qwen-VL (Vision, DashScope compatible-mode)
    qwen_api_key: SecretStr | None = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model_vision: str = "qwen-vl-max-latest"
    qwen_request_timeout_s: float = 30.0

    # MiniMax (TTS)
    minimax_api_key: SecretStr | None = None
    minimax_group_id: str | None = None
    minimax_base_url: str = "https://api.minimaxi.chat/v1"
    minimax_model_tts: str = "speech-02-hd"
    minimax_default_voice: str = "English_expressive_narrator"
    minimax_request_timeout_s: float = 30.0
```

Replace the existing `_validate_provider_credentials` with per-provider checks:

```python
    @model_validator(mode="after")
    def _validate_provider_credentials(self) -> Settings:
        uses_openai = "openai" in (
            self.ai_vision_provider,
            self.ai_llm_provider,
            self.ai_tts_provider,
            self.ai_stt_provider,
        )
        if uses_openai and self.openai_api_key is None:
            raise ValueError(
                "PLL_OPENAI_API_KEY is required when any AI provider is set to 'openai'"
            )
        if self.ai_llm_provider == "deepseek" and self.deepseek_api_key is None:
            raise ValueError(
                "PLL_DEEPSEEK_API_KEY is required when LLM provider is 'deepseek'"
            )
        if self.ai_vision_provider == "qwen" and self.qwen_api_key is None:
            raise ValueError(
                "PLL_QWEN_API_KEY is required when vision provider is 'qwen'"
            )
        if self.ai_tts_provider == "minimax":
            if self.minimax_api_key is None:
                raise ValueError(
                    "PLL_MINIMAX_API_KEY is required when TTS provider is 'minimax'"
                )
            if not self.minimax_group_id:
                raise ValueError(
                    "PLL_MINIMAX_GROUP_ID is required when TTS provider is 'minimax'"
                )
        return self
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_config.py -v`
Expected: all config tests pass (existing OpenAI tests + 6 new tests).

- [ ] **Step 5: Update `.env.example`** — append after the existing `PLL_OPENAI_*` block:

```dotenv
# === DeepSeek (LLM, OpenAI-compatible) ===
# Set PLL_AI_LLM_PROVIDER=deepseek to enable.
# PLL_DEEPSEEK_API_KEY=sk-...
# PLL_DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
# PLL_DEEPSEEK_MODEL_LLM=deepseek-v4-flash

# === Qwen-VL (Vision, DashScope compatible-mode) ===
# Set PLL_AI_VISION_PROVIDER=qwen to enable.
# Get key at https://dashscope.console.aliyun.com/.
# PLL_QWEN_API_KEY=sk-...
# PLL_QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# PLL_QWEN_MODEL_VISION=qwen-vl-max-latest

# === MiniMax (TTS, speech-02-hd) ===
# Set PLL_AI_TTS_PROVIDER=minimax to enable.
# Both key AND group_id required (group_id is sent as query param).
# PLL_MINIMAX_API_KEY=...
# PLL_MINIMAX_GROUP_ID=...
# PLL_MINIMAX_MODEL_TTS=speech-02-hd
# PLL_MINIMAX_DEFAULT_VOICE=English_expressive_narrator
```

- [ ] **Step 6: Commit**

```bash
git add app/config.py tests/test_config.py .env.example
git commit -m "feat(config): add deepseek/qwen/minimax provider settings"
```

---

## Sub-phase 6.2 — DeepSeek-V4 LLM adapter

DeepSeek's API is OpenAI-compatible: same `/chat/completions` endpoint, same SSE streaming with `data: ` prefix and `[DONE]` terminator. The adapter is a near-clone of `OpenAILLMAdapter` with different `provider` label in error messages and different default base URL.

**Files:**
- Create: `app/adapters/llm/deepseek_llm.py`
- Create: `tests/test_deepseek_llm_adapter.py`

### Task 6.2.1: Write failing tests

- [ ] **Step 1: Write the failing tests** in `tests/test_deepseek_llm_adapter.py` (full file)

```python
"""Tests for DeepSeekLLMAdapter (httpx mocked via respx)."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError

DS_URL = "https://api.deepseek.com/v1/chat/completions"


def _build_single_response(text: str) -> dict:
    return {
        "id": "chatcmpl-x",
        "object": "chat.completion",
        "created": 0,
        "model": "deepseek-v4-flash",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
        ],
    }


def _build_stream_chunk(content: str | None) -> str:
    data = {"choices": [{"index": 0, "delta": {"content": content} if content else {}}]}
    return f"data: {json.dumps(data)}\n\n"


@pytest.mark.asyncio
@respx.mock
async def test_single_response_returns_text():
    from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter

    respx.post(DS_URL).mock(
        return_value=httpx.Response(200, json=_build_single_response("Hello DeepSeek!"))
    )

    adapter = DeepSeekLLMAdapter(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-flash",
        timeout_s=10.0,
    )
    result = await adapter.generate([{"role": "user", "content": "Say hi"}])
    assert result == "Hello DeepSeek!"


@pytest.mark.asyncio
@respx.mock
async def test_streaming_yields_tokens_in_order():
    from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter

    chunks = [
        _build_stream_chunk("Hello"),
        _build_stream_chunk(" "),
        _build_stream_chunk("DeepSeek"),
        _build_stream_chunk("!"),
        _build_stream_chunk(None),
        "data: [DONE]\n\n",
    ]
    body = "".join(chunks)

    respx.post(DS_URL).mock(return_value=httpx.Response(200, text=body))

    adapter = DeepSeekLLMAdapter(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-flash",
        timeout_s=10.0,
    )
    tokens = []
    async for token in adapter.generate_stream([{"role": "user", "content": "Say hi"}]):
        tokens.append(token)
    assert "".join(tokens) == "Hello DeepSeek!"


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter

    respx.post(DS_URL).mock(return_value=httpx.Response(500, text="server error"))

    adapter = DeepSeekLLMAdapter(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-flash",
        timeout_s=10.0,
    )
    with pytest.raises(UpstreamFailureError) as exc_info:
        await adapter.generate([{"role": "user", "content": "Hi"}])
    assert exc_info.value.provider == "deepseek"


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter

    respx.post(DS_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    adapter = DeepSeekLLMAdapter(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-flash",
        timeout_s=10.0,
    )
    with pytest.raises(UpstreamTimeoutError) as exc_info:
        await adapter.generate([{"role": "user", "content": "Hi"}])
    assert exc_info.value.provider == "deepseek"


@pytest.mark.asyncio
@respx.mock
async def test_stream_http_500_raises_upstream_failure():
    from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter

    respx.post(DS_URL).mock(return_value=httpx.Response(500, text="server error"))

    adapter = DeepSeekLLMAdapter(
        api_key="sk-test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-flash",
        timeout_s=10.0,
    )
    with pytest.raises(UpstreamFailureError):
        async for _ in adapter.generate_stream([{"role": "user", "content": "Hi"}]):
            pass


@pytest.mark.asyncio
@respx.mock
async def test_request_uses_bearer_auth_and_model():
    from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter

    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=_build_single_response("ok"))

    respx.post(DS_URL).mock(side_effect=_capture)

    adapter = DeepSeekLLMAdapter(
        api_key="sk-secret",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-flash",
        timeout_s=10.0,
    )
    await adapter.generate([{"role": "user", "content": "Hi"}])

    assert captured["headers"].get("authorization") == "Bearer sk-secret"
    assert captured["body"]["model"] == "deepseek-v4-flash"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_deepseek_llm_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.adapters.llm.deepseek_llm'`.

### Task 6.2.2: Implement adapter

- [ ] **Step 3: Create `app/adapters/llm/deepseek_llm.py`** (full file)

```python
"""DeepSeek Chat Completions adapter (OpenAI-compatible) for text-generation LLM."""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import httpx
import structlog

from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.deepseek_llm")

_PROVIDER = "deepseek"


class DeepSeekLLMAdapter:
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

    async def generate(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> str:
        url = f"{self._base_url}/chat/completions"
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("deepseek.llm.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider=_PROVIDER) from exc
        except httpx.HTTPError as exc:
            log.warning("deepseek.llm.http_error", error=str(exc))
            raise UpstreamFailureError(provider=_PROVIDER, message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("deepseek.llm.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider=_PROVIDER,
                message=f"deepseek returned {resp.status_code}",
            )

        try:
            envelope = resp.json()
            return envelope["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("deepseek.llm.parse_error", error=str(exc))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="invalid response from upstream"
            ) from exc

    async def generate_stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        url = f"{self._base_url}/chat/completions"
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                async with client.stream("POST", url, json=body, headers=headers) as resp:
                    if resp.status_code >= 400:
                        log.warning("deepseek.llm.stream_http_status", status=resp.status_code)
                        raise UpstreamFailureError(
                            provider=_PROVIDER,
                            message=f"deepseek returned {resp.status_code}",
                        )
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line.removeprefix("data: ").strip()
                        if payload == "[DONE]":
                            return
                        try:
                            chunk = json.loads(payload)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except httpx.TimeoutException as exc:
            log.warning("deepseek.llm.stream_timeout", error=str(exc))
            raise UpstreamTimeoutError(provider=_PROVIDER) from exc
        except httpx.HTTPError as exc:
            log.warning("deepseek.llm.stream_http_error", error=str(exc))
            raise UpstreamFailureError(provider=_PROVIDER, message=str(exc)) from exc
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_deepseek_llm_adapter.py -v`
Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/adapters/llm/deepseek_llm.py tests/test_deepseek_llm_adapter.py
git commit -m "feat(llm): add DeepSeek-V4 adapter (OpenAI-compatible)"
```

---

## Sub-phase 6.3 — Qwen-VL-Max vision adapter

DashScope's compatible-mode endpoint accepts the OpenAI chat-completions schema with `image_url` parts. The adapter reuses `build_vision_safety_messages` and the same JSON parsing as `OpenAIVisionAdapter`. Only the base URL, default model, and the `provider` label in errors differ. We extract the shared payload-parsing helper to keep both adapters DRY.

**Files:**
- Create: `app/adapters/vision/qwen_vision.py`
- Create: `tests/test_qwen_vision_adapter.py`

### Task 6.3.1: Write failing tests

- [ ] **Step 1: Write the failing tests** in `tests/test_qwen_vision_adapter.py` (full file)

```python
"""Tests for QwenVisionAdapter (DashScope compatible-mode, mocked via respx)."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError
from tests.fixtures.images import safe_png_bytes

QWEN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def _build_response(json_payload: dict) -> dict:
    """Wrap a vision JSON object in the OpenAI chat-completions envelope."""
    return {
        "id": "chatcmpl-q",
        "object": "chat.completion",
        "created": 0,
        "model": "qwen-vl-max-latest",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(json_payload)},
                "finish_reason": "stop",
            }
        ],
    }


def _build_adapter():
    from app.adapters.vision.qwen_vision import QwenVisionAdapter

    return QwenVisionAdapter(
        api_key="sk-qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-vl-max-latest",
        timeout_s=10.0,
    )


@pytest.mark.asyncio
@respx.mock
async def test_parses_safe_response_into_vision_result():
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
        ],
    }
    respx.post(QWEN_URL).mock(return_value=httpx.Response(200, json=_build_response(payload)))

    adapter = _build_adapter()
    result = await adapter.analyze_image(safe_png_bytes())

    assert result.is_safe is True
    assert result.scene_summary == "A modern kitchen."
    assert len(result.objects) == 1
    assert result.objects[0].label == "cupcake"


@pytest.mark.asyncio
@respx.mock
async def test_parses_unsafe_response():
    payload = {
        "is_safe": False,
        "reject_reasons": ["face_detected"],
        "scene_summary": "",
        "objects": [],
    }
    respx.post(QWEN_URL).mock(return_value=httpx.Response(200, json=_build_response(payload)))

    adapter = _build_adapter()
    result = await adapter.analyze_image(safe_png_bytes())

    assert result.is_safe is False
    assert "face_detected" in result.reject_reasons


@pytest.mark.asyncio
@respx.mock
async def test_assigns_object_ids_when_provider_omits_them():
    payload = {
        "is_safe": True,
        "reject_reasons": [],
        "scene_summary": "scene",
        "objects": [
            {"label": "apple", "bbox": [0.1, 0.1, 0.1, 0.1]},
            {"label": "pear", "bbox": [0.2, 0.2, 0.1, 0.1]},
        ],
    }
    respx.post(QWEN_URL).mock(return_value=httpx.Response(200, json=_build_response(payload)))

    adapter = _build_adapter()
    result = await adapter.analyze_image(safe_png_bytes())

    ids = [o.id for o in result.objects]
    assert len(set(ids)) == 2
    assert all(i for i in ids)


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    respx.post(QWEN_URL).mock(return_value=httpx.Response(500, text="server error"))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError) as exc_info:
        await adapter.analyze_image(safe_png_bytes())
    assert exc_info.value.provider == "qwen"


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    respx.post(QWEN_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    adapter = _build_adapter()
    with pytest.raises(UpstreamTimeoutError) as exc_info:
        await adapter.analyze_image(safe_png_bytes())
    assert exc_info.value.provider == "qwen"


@pytest.mark.asyncio
@respx.mock
async def test_invalid_json_in_response_raises_upstream_failure():
    bad_envelope = {
        "choices": [{"message": {"content": "not-json-at-all"}, "finish_reason": "stop"}]
    }
    respx.post(QWEN_URL).mock(return_value=httpx.Response(200, json=bad_envelope))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError):
        await adapter.analyze_image(safe_png_bytes())


@pytest.mark.asyncio
@respx.mock
async def test_request_includes_authorization_header_and_image_data_url():
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

    respx.post(QWEN_URL).mock(side_effect=_capture)

    adapter = _build_adapter()
    await adapter.analyze_image(safe_png_bytes())

    assert captured["headers"].get("authorization") == "Bearer sk-qwen"
    assert captured["body"]["model"] == "qwen-vl-max-latest"
    user_msg = captured["body"]["messages"][1]
    image_part = next(p for p in user_msg["content"] if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/")
    assert "base64," in image_part["image_url"]["url"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_qwen_vision_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.adapters.vision.qwen_vision'`.

### Task 6.3.2: Implement adapter

- [ ] **Step 3: Create `app/adapters/vision/qwen_vision.py`** (full file)

```python
"""Qwen-VL adapter via DashScope compatible-mode (OpenAI-compatible chat completions)."""
from __future__ import annotations

import json

import httpx
import structlog

from app.adapters.vision.base import VisionIntent
from app.adapters.vision.openai_vision import _payload_to_result, _to_data_url
from app.errors import UpstreamFailureError, UpstreamTimeoutError
from app.prompts.vision_safety import build_vision_safety_messages
from app.schemas.vision import VisionResult

log = structlog.get_logger("pll.adapter.qwen_vision")

_PROVIDER = "qwen"


class QwenVisionAdapter:
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
        intent: VisionIntent = "safety_and_objects",
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
            log.warning("qwen.vision.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider=_PROVIDER) from exc
        except httpx.HTTPError as exc:
            log.warning("qwen.vision.http_error", error=str(exc))
            raise UpstreamFailureError(provider=_PROVIDER, message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("qwen.vision.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider=_PROVIDER,
                message=f"qwen returned {resp.status_code}",
            )

        try:
            envelope = resp.json()
            content_str = envelope["choices"][0]["message"]["content"]
            payload = json.loads(content_str)
        except (KeyError, IndexError, ValueError) as exc:
            log.warning("qwen.vision.parse_error", error=str(exc))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="invalid JSON from upstream"
            ) from exc

        return _payload_to_result(payload)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_qwen_vision_adapter.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/adapters/vision/qwen_vision.py tests/test_qwen_vision_adapter.py
git commit -m "feat(vision): add Qwen-VL-Max adapter via DashScope compatible-mode"
```

---

## Sub-phase 6.4 — MiniMax TTS adapter (speech-02-hd)

MiniMax's T2A v2 API differs from OpenAI's `/audio/speech` in three ways:

1. **Auth dual-channel:** `Authorization: Bearer <api_key>` header **plus** `GroupId=<group_id>` query parameter — both required.
2. **JSON envelope, not raw bytes:** response is JSON with `data.audio` containing the audio as a hex-encoded string and `base_resp.status_code` for application-level errors (0 = success).
3. **Voice + audio settings:** voice_id (e.g. `English_expressive_narrator`), speed, vol, pitch live in `voice_setting`; format/bitrate live in `audio_setting`.

The adapter accepts a `voice` argument (mapped to `voice_id`) so it slots into the existing `TTSAdapter` Protocol.

**Files:**
- Create: `app/adapters/tts/minimax_tts.py`
- Create: `tests/test_minimax_tts_adapter.py`

### Task 6.4.1: Write failing tests

- [ ] **Step 1: Write the failing tests** in `tests/test_minimax_tts_adapter.py` (full file)

```python
"""Tests for MiniMaxTTSAdapter (httpx mocked via respx)."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.errors import UpstreamFailureError, UpstreamTimeoutError

MM_URL = "https://api.minimaxi.chat/v1/t2a_v2"


def _build_adapter():
    from app.adapters.tts.minimax_tts import MiniMaxTTSAdapter

    return MiniMaxTTSAdapter(
        api_key="sk-mm",
        group_id="grp123",
        base_url="https://api.minimaxi.chat/v1",
        model="speech-02-hd",
        default_voice="English_expressive_narrator",
        timeout_s=10.0,
    )


def _success_envelope(audio_hex: str) -> dict:
    return {
        "data": {"audio": audio_hex, "status": 2},
        "trace_id": "trace-x",
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }


@pytest.mark.asyncio
@respx.mock
async def test_synthesize_decodes_hex_audio():
    from app.adapters.tts.minimax_tts import MiniMaxTTSAdapter

    audio_bytes = b"\xff\xfb\x50\xc4fake-mp3"
    respx.post(MM_URL).mock(
        return_value=httpx.Response(200, json=_success_envelope(audio_bytes.hex()))
    )

    adapter = _build_adapter()
    result = await adapter.synthesize("Hello")
    assert result == audio_bytes


@pytest.mark.asyncio
@respx.mock
async def test_request_uses_group_id_query_and_bearer_auth():
    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=_success_envelope(b"abc".hex()))

    respx.post(MM_URL).mock(side_effect=_capture)

    adapter = _build_adapter()
    await adapter.synthesize("Hello", voice="English_friendly_female")

    assert "GroupId=grp123" in captured["url"]
    assert captured["headers"].get("authorization") == "Bearer sk-mm"
    assert captured["body"]["model"] == "speech-02-hd"
    assert captured["body"]["text"] == "Hello"
    assert captured["body"]["voice_setting"]["voice_id"] == "English_friendly_female"
    assert captured["body"]["audio_setting"]["format"] == "mp3"


@pytest.mark.asyncio
@respx.mock
async def test_default_voice_used_when_voice_arg_is_alloy_or_blank():
    """The orchestrator currently passes voice="alloy" (legacy default).
    For MiniMax, fall back to the configured default_voice in that case."""
    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=_success_envelope(b"abc".hex()))

    respx.post(MM_URL).mock(side_effect=_capture)

    adapter = _build_adapter()
    await adapter.synthesize("Hello", voice="alloy")

    assert captured["body"]["voice_setting"]["voice_id"] == "English_expressive_narrator"


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_upstream_failure():
    respx.post(MM_URL).mock(return_value=httpx.Response(500, text="server error"))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError) as exc_info:
        await adapter.synthesize("Hello")
    assert exc_info.value.provider == "minimax"


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_upstream_timeout():
    respx.post(MM_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    adapter = _build_adapter()
    with pytest.raises(UpstreamTimeoutError) as exc_info:
        await adapter.synthesize("Hello")
    assert exc_info.value.provider == "minimax"


@pytest.mark.asyncio
@respx.mock
async def test_application_error_in_base_resp_raises_upstream_failure():
    """HTTP 200 but base_resp.status_code != 0 = application-level failure."""
    bad_envelope = {
        "data": {},
        "base_resp": {"status_code": 1004, "status_msg": "voice_id not found"},
    }
    respx.post(MM_URL).mock(return_value=httpx.Response(200, json=bad_envelope))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError) as exc_info:
        await adapter.synthesize("Hello")
    assert "1004" in str(exc_info.value) or "voice_id not found" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_missing_audio_field_raises_upstream_failure():
    bad_envelope = {
        "data": {"status": 2},  # no 'audio' key
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }
    respx.post(MM_URL).mock(return_value=httpx.Response(200, json=bad_envelope))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError):
        await adapter.synthesize("Hello")


@pytest.mark.asyncio
@respx.mock
async def test_invalid_hex_in_audio_raises_upstream_failure():
    bad_envelope = {
        "data": {"audio": "not-valid-hex-string-zzz", "status": 2},
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }
    respx.post(MM_URL).mock(return_value=httpx.Response(200, json=bad_envelope))

    adapter = _build_adapter()
    with pytest.raises(UpstreamFailureError):
        await adapter.synthesize("Hello")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_minimax_tts_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.adapters.tts.minimax_tts'`.

### Task 6.4.2: Implement adapter

- [ ] **Step 3: Create `app/adapters/tts/minimax_tts.py`** (full file)

```python
"""MiniMax T2A v2 adapter (speech-02-hd).

Differences from OpenAI TTS:
  - GroupId is required as a URL query parameter (not in body or headers).
  - Response is a JSON envelope; audio bytes come back hex-encoded under data.audio.
  - Application-level errors are signaled via base_resp.status_code (0 = success).
"""
from __future__ import annotations

import httpx
import structlog

from app.errors import UpstreamFailureError, UpstreamTimeoutError

log = structlog.get_logger("pll.adapter.minimax_tts")

_PROVIDER = "minimax"

# The legacy default voice from the OpenAI adapter; remap to the MiniMax default.
_LEGACY_VOICE_ALIASES = {"alloy", "", None}


class MiniMaxTTSAdapter:
    def __init__(
        self,
        *,
        api_key: str,
        group_id: str,
        base_url: str,
        model: str,
        default_voice: str,
        timeout_s: float,
    ) -> None:
        self._api_key = api_key
        self._group_id = group_id
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._default_voice = default_voice
        self._timeout_s = timeout_s

    async def synthesize(
        self,
        text: str,
        *,
        voice: str = "alloy",
    ) -> bytes:
        voice_id = voice if voice not in _LEGACY_VOICE_ALIASES else self._default_voice

        url = f"{self._base_url}/t2a_v2"
        params = {"GroupId": self._group_id}
        body = {
            "model": self._model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(url, params=params, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            log.warning("minimax.tts.timeout", error=str(exc))
            raise UpstreamTimeoutError(provider=_PROVIDER) from exc
        except httpx.HTTPError as exc:
            log.warning("minimax.tts.http_error", error=str(exc))
            raise UpstreamFailureError(provider=_PROVIDER, message=str(exc)) from exc

        if resp.status_code >= 400:
            log.warning("minimax.tts.http_status", status=resp.status_code, body=resp.text[:500])
            raise UpstreamFailureError(
                provider=_PROVIDER,
                message=f"minimax returned {resp.status_code}",
            )

        try:
            envelope = resp.json()
        except ValueError as exc:
            log.warning("minimax.tts.invalid_json", error=str(exc))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="invalid JSON from upstream"
            ) from exc

        base_resp = envelope.get("base_resp") or {}
        status_code = base_resp.get("status_code")
        if status_code not in (0, None):
            msg = base_resp.get("status_msg") or "unknown"
            log.warning("minimax.tts.app_error", status_code=status_code, status_msg=msg)
            raise UpstreamFailureError(
                provider=_PROVIDER,
                message=f"minimax application error {status_code}: {msg}",
            )

        audio_hex = (envelope.get("data") or {}).get("audio")
        if not audio_hex:
            log.warning("minimax.tts.missing_audio", envelope_keys=list(envelope.keys()))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="response missing data.audio"
            )

        try:
            return bytes.fromhex(audio_hex)
        except ValueError as exc:
            log.warning("minimax.tts.invalid_hex", error=str(exc))
            raise UpstreamFailureError(
                provider=_PROVIDER, message="data.audio is not valid hex"
            ) from exc
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_minimax_tts_adapter.py -v`
Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/adapters/tts/minimax_tts.py tests/test_minimax_tts_adapter.py
git commit -m "feat(tts): add MiniMax speech-02-hd adapter with hex audio decoding"
```

---

## Sub-phase 6.5 — Voice picker + persona/orchestrator wiring

PRD §4.5 calls for character-matched voices (cake → sweet female, wrench → gruff male, etc.). MiniMax exposes 300+ English voice IDs; we map the persona's `voice_traits` (gender, age, tone) to a curated subset.

Flow:
1. Persona-gen LLM prompt now also emits `voice_traits: {gender, age, tone}`.
2. New `voice_picker.pick_voice(voice_traits) -> str` returns a MiniMax voice_id.
3. `PersonaGenerateResponse` gains `voice_id: str`.
4. Frontend stores `voice_id`, sends it in the WS init frame.
5. `ChatOrchestrator.chat_stream(..., voice_id=...)` passes it to TTS.

**Files:**
- Create: `app/services/voice_picker.py`
- Create: `tests/test_voice_picker.py`
- Modify: `app/schemas/persona.py` (add `voice_id`)
- Modify: `app/prompts/persona_gen.py` (emit `voice_traits`)
- Modify: `app/services/persona_service.py` (call voice_picker)
- Modify: `app/services/chat_orchestrator.py` (accept `voice_id` arg)
- Modify: `app/api/chat.py` (read `voice_id` from init frame)
- Modify: `tests/test_persona_service.py`, `tests/test_chat_orchestrator.py`, `tests/test_chat_api.py`

### Task 6.5.1: VoicePicker service

- [ ] **Step 1: Write the failing test** in `tests/test_voice_picker.py` (full file)

```python
"""Tests for voice_picker — maps persona traits to MiniMax voice IDs."""
from __future__ import annotations

import pytest


def test_female_warm_returns_female_voice():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": "female", "age": "adult", "tone": "warm"})
    assert "female" in voice_id.lower() or "woman" in voice_id.lower()


def test_male_gruff_returns_male_voice():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": "male", "age": "adult", "tone": "gruff"})
    assert "male" in voice_id.lower() or "man" in voice_id.lower()


def test_child_returns_child_voice():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": "female", "age": "child", "tone": "playful"})
    assert "child" in voice_id.lower() or "kid" in voice_id.lower() or "young" in voice_id.lower()


def test_empty_traits_returns_fallback():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({})
    assert voice_id == "English_expressive_narrator"


def test_unknown_gender_returns_fallback():
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": "robot", "age": "adult", "tone": "warm"})
    assert voice_id == "English_expressive_narrator"


def test_pick_voice_is_deterministic():
    from app.services.voice_picker import pick_voice

    traits = {"gender": "female", "age": "adult", "tone": "warm"}
    assert pick_voice(traits) == pick_voice(traits)


@pytest.mark.parametrize(
    "gender,expected_keyword",
    [("female", "female"), ("male", "male")],
)
def test_each_gender_maps_to_distinct_voice_pool(gender, expected_keyword):
    from app.services.voice_picker import pick_voice

    voice_id = pick_voice({"gender": gender, "age": "adult", "tone": "neutral"})
    assert expected_keyword in voice_id.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_voice_picker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.voice_picker'`.

- [ ] **Step 3: Create `app/services/voice_picker.py`** (full file)

```python
"""voice_picker: map persona voice_traits dict to a MiniMax voice_id.

Voice IDs reference: https://platform.minimaxi.com/document/T2A%20V2
Curated subset of English voices selected for clarity and character variety.
"""
from __future__ import annotations

FALLBACK_VOICE = "English_expressive_narrator"

# (gender, age, tone) -> voice_id. Lookup order: exact → (gender, age) → (gender) → fallback.
_VOICE_TABLE: dict[tuple[str, str, str], str] = {
    # Female adult — different tones
    ("female", "adult", "warm"):     "English_friendly_female",
    ("female", "adult", "sweet"):    "English_sweet_female",
    ("female", "adult", "confident"):"English_confident_female",
    ("female", "adult", "neutral"):  "English_calm_female",
    ("female", "adult", "playful"):  "English_playful_female",
    # Male adult — different tones
    ("male", "adult", "warm"):       "English_friendly_male",
    ("male", "adult", "gruff"):      "English_deep_male",
    ("male", "adult", "confident"):  "English_confident_male",
    ("male", "adult", "neutral"):    "English_calm_male",
    ("male", "adult", "playful"):    "English_cheerful_male",
    # Children — gender + playful tones
    ("female", "child", "playful"):  "English_young_girl",
    ("female", "child", "sweet"):    "English_young_girl",
    ("male", "child", "playful"):    "English_young_boy",
    # Elder
    ("female", "elder", "warm"):     "English_wise_grandma",
    ("male", "elder", "gruff"):      "English_wise_grandpa",
}

# (gender, age) -> default voice when tone is missing or unknown.
_GENDER_AGE_DEFAULTS: dict[tuple[str, str], str] = {
    ("female", "adult"): "English_friendly_female",
    ("male", "adult"): "English_friendly_male",
    ("female", "child"): "English_young_girl",
    ("male", "child"): "English_young_boy",
    ("female", "elder"): "English_wise_grandma",
    ("male", "elder"): "English_wise_grandpa",
}

# gender only -> default.
_GENDER_DEFAULTS: dict[str, str] = {
    "female": "English_friendly_female",
    "male": "English_friendly_male",
}


def pick_voice(voice_traits: dict | None) -> str:
    """Return a MiniMax voice_id for the given persona traits, with graceful fallback."""
    if not voice_traits:
        return FALLBACK_VOICE

    gender = str(voice_traits.get("gender") or "").lower()
    age = str(voice_traits.get("age") or "adult").lower()
    tone = str(voice_traits.get("tone") or "").lower()

    if gender not in {"male", "female"}:
        return FALLBACK_VOICE

    if (gender, age, tone) in _VOICE_TABLE:
        return _VOICE_TABLE[(gender, age, tone)]
    if (gender, age) in _GENDER_AGE_DEFAULTS:
        return _GENDER_AGE_DEFAULTS[(gender, age)]
    if gender in _GENDER_DEFAULTS:
        return _GENDER_DEFAULTS[gender]
    return FALLBACK_VOICE
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_voice_picker.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/voice_picker.py tests/test_voice_picker.py
git commit -m "feat(persona): add voice_picker mapping traits to MiniMax voice IDs"
```

### Task 6.5.2: Add `voice_id` to PersonaGenerateResponse

- [ ] **Step 1: Write the failing test** — append to `tests/test_persona_service.py`

```python
@pytest.mark.asyncio
async def test_persona_response_includes_voice_id_from_picker(monkeypatch):
    """PersonaService should populate voice_id by calling voice_picker on the LLM's voice_traits."""
    from app.services.persona_service import PersonaService
    from app.schemas.persona import PersonaGenerateRequest

    class FakeLLM:
        async def generate(self, messages, *, temperature=0.8):
            import json
            return json.dumps({
                "persona_name": "Sweet Cupcake",
                "description": "A cheerful baked good",
                "system_prompt": "Be sweet",
                "vocab_focus": ["sweet"],
                "voice_traits": {"gender": "female", "age": "adult", "tone": "sweet"},
            })

    svc = PersonaService(llm=FakeLLM())
    result = await svc.generate_persona(
        PersonaGenerateRequest(label="cupcake", scene_summary="kitchen", user_level="beginner")
    )
    assert result.voice_id == "English_sweet_female"


@pytest.mark.asyncio
async def test_persona_response_voice_id_fallback_when_traits_missing():
    from app.services.persona_service import PersonaService
    from app.schemas.persona import PersonaGenerateRequest

    class FakeLLM:
        async def generate(self, messages, *, temperature=0.8):
            import json
            return json.dumps({
                "persona_name": "Mystery",
                "description": "Unknown",
                "system_prompt": "Be mysterious",
                "vocab_focus": [],
                # no voice_traits
            })

    svc = PersonaService(llm=FakeLLM())
    result = await svc.generate_persona(
        PersonaGenerateRequest(label="thing", scene_summary="", user_level="beginner")
    )
    assert result.voice_id == "English_expressive_narrator"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_persona_service.py -k voice_id -v`
Expected: FAIL — `PersonaGenerateResponse` has no `voice_id` field.

- [ ] **Step 3: Modify `app/schemas/persona.py`** — add `voice_id`

```python
class PersonaGenerateResponse(BaseModel):
    persona_id: str
    persona_name: str
    description: str
    system_prompt: str
    vocab_focus: list[str] = Field(default_factory=list)
    voice_id: str = Field(default="English_expressive_narrator")
```

- [ ] **Step 4: Modify `app/services/persona_service.py`** — call `pick_voice` and populate

Add import at top:

```python
from app.services.voice_picker import pick_voice
```

Inside `generate_persona`, replace the `PersonaGenerateResponse(...)` construction with:

```python
            response = PersonaGenerateResponse(
                persona_id=uuid4().hex[:8],
                persona_name=data["persona_name"],
                description=data.get(
                    "personality_description",
                    data.get("description", ""),
                ),
                system_prompt=data["system_prompt"],
                vocab_focus=data.get("vocab_focus", []),
                voice_id=pick_voice(data.get("voice_traits")),
            )
```

- [ ] **Step 5: Modify `app/prompts/persona_gen.py`** — extend the system prompt to ask for `voice_traits`

Replace the existing JSON-keys list block with:

```python
        "Output strict JSON with these keys:\n"
        "- persona_name: a creative English name for this object\n"
        "- description: 1-2 sentence personality description in English\n"
        "- system_prompt: instructions for how this persona speaks (voice, attitude, vocabulary style)\n"
        "- vocab_focus: 3-6 English vocabulary words this persona would naturally teach\n"
        "- voice_traits: {gender, age, tone} for TTS voice selection\n"
        "    gender: 'female' | 'male'\n"
        "    age: 'child' | 'adult' | 'elder'\n"
        "    tone: 'warm' | 'sweet' | 'confident' | 'neutral' | 'playful' | 'gruff'\n\n"
```

- [ ] **Step 6: Run tests to verify pass**

Run: `pytest tests/test_persona_service.py -v`
Expected: all persona service tests pass (existing + 2 new).

- [ ] **Step 7: Commit**

```bash
git add app/schemas/persona.py app/services/persona_service.py app/prompts/persona_gen.py tests/test_persona_service.py
git commit -m "feat(persona): emit voice_id from picker, request voice_traits from LLM"
```

### Task 6.5.3: Thread `voice_id` through ChatOrchestrator

- [ ] **Step 1: Write the failing test** — append to `tests/test_chat_orchestrator.py`

```python
@pytest.mark.asyncio
async def test_chat_stream_passes_voice_id_to_tts():
    """Orchestrator must pass voice_id to TTS instead of hardcoded 'alloy'."""
    from app.services.chat_orchestrator import ChatOrchestrator
    from app.services.context_manager import ContextManager

    captured_voice = {}

    class FakeLLM:
        async def generate_stream(self, messages, *, temperature=0.7):
            for chunk in ["<speak>Hi</speak>", "<learning>l</learning>", "<followup>f</followup>"]:
                yield chunk
        async def generate(self, messages, *, temperature=0.7):
            return ""

    class FakeTTS:
        async def synthesize(self, text, *, voice="alloy"):
            captured_voice["voice"] = voice
            return b"audio"

    orch = ChatOrchestrator(llm=FakeLLM(), tts=FakeTTS(), context=ContextManager(llm=FakeLLM()))

    events = []
    async for ev in orch.chat_stream(
        "sess1",
        "Hello",
        system_message={"role": "system", "content": "Be a cake"},
        voice_id="English_sweet_female",
    ):
        events.append(ev)

    assert captured_voice["voice"] == "English_sweet_female"


@pytest.mark.asyncio
async def test_chat_stream_defaults_voice_id_when_omitted():
    """When voice_id is None (legacy callers), orchestrator falls back to 'alloy'."""
    from app.services.chat_orchestrator import ChatOrchestrator
    from app.services.context_manager import ContextManager

    captured_voice = {}

    class FakeLLM:
        async def generate_stream(self, messages, *, temperature=0.7):
            yield "<speak>Hi</speak><learning>l</learning><followup>f</followup>"
        async def generate(self, messages, *, temperature=0.7):
            return ""

    class FakeTTS:
        async def synthesize(self, text, *, voice="alloy"):
            captured_voice["voice"] = voice
            return b"audio"

    orch = ChatOrchestrator(llm=FakeLLM(), tts=FakeTTS(), context=ContextManager(llm=FakeLLM()))
    async for _ in orch.chat_stream(
        "sess2",
        "Hello",
        system_message={"role": "system", "content": "x"},
    ):
        pass

    assert captured_voice["voice"] == "alloy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_chat_orchestrator.py -k voice -v`
Expected: FAIL — `chat_stream() got an unexpected keyword argument 'voice_id'`.

- [ ] **Step 3: Modify `app/services/chat_orchestrator.py`**

Change `chat_stream` signature to accept `voice_id`:

```python
    async def chat_stream(
        self,
        session_id: str,
        user_message: str,
        system_message: dict,
        learner_context_message: dict | None = None,
        voice_id: str | None = None,
    ) -> AsyncGenerator[dict, None]:
```

Use it in both `synthesize` calls. Replace the hardcoded `voice="alloy"`:

```python
            effective_voice = voice_id or "alloy"
            ...
                if not speak_text_emitted and "</speak>" in full_response:
                    speak_text = self._extract_tag(full_response, "speak")
                    yield {"type": "speak_text", "content": speak_text}
                    tts_task = asyncio.create_task(
                        self._tts.synthesize(speak_text, voice=effective_voice)
                    )
                    speak_text_emitted = True
            ...
            if tts_task is None:
                audio_bytes = await self._tts.synthesize(segments.speak, voice=effective_voice)
```

Place `effective_voice = voice_id or "alloy"` near the top of `chat_stream`'s `try` block, right after fetching context.

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_chat_orchestrator.py -v`
Expected: all chat_orchestrator tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/chat_orchestrator.py tests/test_chat_orchestrator.py
git commit -m "feat(chat): thread voice_id through ChatOrchestrator to TTS"
```

### Task 6.5.4: Accept `voice_id` in WS init frame

- [ ] **Step 1: Write the failing test** — append to `tests/test_chat_api.py` (or wherever WS tests live)

```python
@pytest.mark.asyncio
async def test_websocket_init_frame_accepts_voice_id(monkeypatch):
    """If init frame includes voice_id, it must be forwarded to ChatOrchestrator."""
    from fastapi.testclient import TestClient
    from app.main import create_app

    captured = {}

    class _SpyOrchestrator:
        def __init__(self, *a, **kw): pass
        async def chat_stream(self, session_id, user_message, system_message,
                              learner_context_message=None, voice_id=None):
            captured["voice_id"] = voice_id
            yield {"type": "result", "segments": {"speak": "hi", "learning": "", "followup": ""}, "audio_base64": ""}

    from app.api import chat as chat_module
    monkeypatch.setattr(chat_module, "ChatOrchestrator", _SpyOrchestrator)

    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/api/chat") as ws:
        ws.send_json({
            "type": "init",
            "session_id": "s1",
            "system_message": {"role": "system", "content": "x"},
            "voice_id": "English_sweet_female",
        })
        ws.send_json({"type": "user_message", "content": "Hello"})
        ws.receive_json()  # drain at least one event

    assert captured["voice_id"] == "English_sweet_female"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_chat_api.py -k voice_id -v`
Expected: FAIL — voice_id is `None` because `chat.py` never reads it.

- [ ] **Step 3: Modify `app/api/chat.py`** — read and forward

After the existing `learner_context_message = ...` block, add:

```python
        voice_id: str | None = init_data.get("voice_id")
```

In the chat loop, change the orchestrator call:

```python
            async for event in orchestrator.chat_stream(
                session_id,
                user_message,
                system_message,
                learner_context_message=learner_context_message,
                voice_id=voice_id,
            ):
                await websocket.send_json(event)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_chat_api.py -v`
Expected: all chat_api tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/api/chat.py tests/test_chat_api.py
git commit -m "feat(chat): accept voice_id from WebSocket init frame"
```

### Task 6.5.5: Frontend voice_id plumbing

- [ ] **Step 1: Audit frontend types** to find the persona response shape

Run: `grep -rn "persona_name" frontend/src/`
Expected: identifies the TypeScript interface for the persona API response (likely `frontend/src/lib/api.ts` or similar).

- [ ] **Step 2: Add `voice_id` to the TypeScript persona response type**

In the file from Step 1, add `voice_id: string;` to the persona response interface.

- [ ] **Step 3: Store `voice_id` in Zustand**

In `frontend/src/lib/store.ts`, add to `StudioState`:

```ts
  voiceId: string | null;
  setVoiceId: (v: string | null) => void;
```

And initial state `voiceId: null` plus the setter (`set({ voiceId: v })`).

In `startChat`, accept `voice_id` and store it. Update the signature:

```ts
  startChat: (sessionId: string, personaName: string, personaId: string, voiceId: string) => void;
```

- [ ] **Step 4: Send `voice_id` in the WS init frame**

In `frontend/src/lib/chat.ts` (or wherever the init payload is built), append `voice_id` from the store to the `init` message.

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend && npm test -- --run`
Expected: existing tests pass; if any persona-mock fixture lacks `voice_id`, add it.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): plumb voice_id from persona response into WS init"
```

---

## Sub-phase 6.6 — Factory branches + docs closure

Wire the three new adapters into `factory.py` so changing `PLL_AI_*_PROVIDER=<new>` actually routes to them. Then close the PRD open question and update the README.

**Files:**
- Modify: `app/adapters/factory.py`
- Modify: `tests/test_llm_factory.py`
- Modify: `tests/test_vision_factory.py`
- Modify: `tests/test_tts_factory.py`
- Modify: `docs/plans/README.md`
- Modify: `docs/prd/2026-05-09-personalingualive-prd.md`
- Modify: `README.md`

### Task 6.6.1: Factory branch for DeepSeek

- [ ] **Step 1: Write the failing test** — append to `tests/test_llm_factory.py`

```python
def test_deepseek_provider(monkeypatch):
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("PLL_DEEPSEEK_API_KEY", "sk-ds")
    from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter

    settings = Settings()
    adapter = build_llm_adapter(settings)
    assert isinstance(adapter, DeepSeekLLMAdapter)
    assert adapter._model == "deepseek-v4-flash"
    assert adapter._base_url == "https://api.deepseek.com/v1"


def test_deepseek_provider_without_key_raises(monkeypatch):
    # Settings()'s validator catches missing key before factory runs.
    monkeypatch.setenv("PLL_AI_LLM_PROVIDER", "deepseek")
    import pytest

    with pytest.raises(ValueError, match="PLL_DEEPSEEK_API_KEY"):
        Settings()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_llm_factory.py -k deepseek -v`
Expected: FAIL — factory has no `deepseek` branch.

- [ ] **Step 3: Modify `app/adapters/factory.py`** — add DeepSeek import & branch

Add import:

```python
from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter
```

Inside `build_llm_adapter`, before the final `raise`:

```python
    if settings.ai_llm_provider == "deepseek":
        if settings.deepseek_api_key is None:
            raise RuntimeError("deepseek provider selected but PLL_DEEPSEEK_API_KEY is missing")
        return DeepSeekLLMAdapter(
            api_key=settings.deepseek_api_key.get_secret_value(),
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model_llm,
            timeout_s=settings.deepseek_request_timeout_s,
        )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_llm_factory.py -v`
Expected: all factory LLM tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/adapters/factory.py tests/test_llm_factory.py
git commit -m "feat(factory): route LLM provider=deepseek to DeepSeekLLMAdapter"
```

### Task 6.6.2: Factory branch for Qwen-VL

- [ ] **Step 1: Write the failing test** — append to `tests/test_vision_factory.py`

```python
def test_qwen_provider(monkeypatch):
    monkeypatch.setenv("PLL_AI_VISION_PROVIDER", "qwen")
    monkeypatch.setenv("PLL_QWEN_API_KEY", "sk-qwen")
    from app.adapters.vision.qwen_vision import QwenVisionAdapter

    settings = Settings()
    adapter = build_vision_adapter(settings)
    assert isinstance(adapter, QwenVisionAdapter)
    assert adapter._model == "qwen-vl-max-latest"
    assert adapter._base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_vision_factory.py -k qwen -v`
Expected: FAIL — factory has no `qwen` branch.

- [ ] **Step 3: Modify `app/adapters/factory.py`** — add Qwen import & branch

Add import:

```python
from app.adapters.vision.qwen_vision import QwenVisionAdapter
```

Inside `build_vision_adapter`, before the final `raise`:

```python
    if settings.ai_vision_provider == "qwen":
        if settings.qwen_api_key is None:
            raise RuntimeError("qwen provider selected but PLL_QWEN_API_KEY is missing")
        return QwenVisionAdapter(
            api_key=settings.qwen_api_key.get_secret_value(),
            base_url=settings.qwen_base_url,
            model=settings.qwen_model_vision,
            timeout_s=settings.qwen_request_timeout_s,
        )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_vision_factory.py -v`
Expected: all factory vision tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/adapters/factory.py tests/test_vision_factory.py
git commit -m "feat(factory): route vision provider=qwen to QwenVisionAdapter"
```

### Task 6.6.3: Factory branch for MiniMax

- [ ] **Step 1: Write the failing test** — append to `tests/test_tts_factory.py`

```python
def test_minimax_provider(monkeypatch):
    monkeypatch.setenv("PLL_AI_TTS_PROVIDER", "minimax")
    monkeypatch.setenv("PLL_MINIMAX_API_KEY", "sk-mm")
    monkeypatch.setenv("PLL_MINIMAX_GROUP_ID", "grp123")
    from app.adapters.tts.minimax_tts import MiniMaxTTSAdapter

    settings = Settings()
    adapter = build_tts_adapter(settings)
    assert isinstance(adapter, MiniMaxTTSAdapter)
    assert adapter._model == "speech-02-hd"
    assert adapter._group_id == "grp123"
    assert adapter._default_voice == "English_expressive_narrator"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tts_factory.py -k minimax -v`
Expected: FAIL — factory has no `minimax` branch.

- [ ] **Step 3: Modify `app/adapters/factory.py`** — add MiniMax import & branch

Add import:

```python
from app.adapters.tts.minimax_tts import MiniMaxTTSAdapter
```

Inside `build_tts_adapter`, before the final `raise`:

```python
    if settings.ai_tts_provider == "minimax":
        if settings.minimax_api_key is None or not settings.minimax_group_id:
            raise RuntimeError(
                "minimax provider selected but PLL_MINIMAX_API_KEY / PLL_MINIMAX_GROUP_ID is missing"
            )
        return MiniMaxTTSAdapter(
            api_key=settings.minimax_api_key.get_secret_value(),
            group_id=settings.minimax_group_id,
            base_url=settings.minimax_base_url,
            model=settings.minimax_model_tts,
            default_voice=settings.minimax_default_voice,
            timeout_s=settings.minimax_request_timeout_s,
        )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_tts_factory.py -v`
Expected: all factory TTS tests pass.

- [ ] **Step 5: Run full test suite**

Run: `pytest -q`
Expected: all existing tests + ~25 new tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/adapters/factory.py tests/test_tts_factory.py
git commit -m "feat(factory): route TTS provider=minimax to MiniMaxTTSAdapter"
```

### Task 6.6.4: Update PRD, plans README, and main README

- [ ] **Step 1: Update `docs/prd/2026-05-09-personalingualive-prd.md`**

Close Open Question #1 in §7.2 by replacing whatever current language describes the unresolved AI vendor question with:

```markdown
1. **AI 厂商策略(已在 v0.2 确定):** 默认使用国产组合 — Qwen-VL-Max(视觉)+ DeepSeek-V4-Flash(LLM)+ MiniMax speech-02-hd(TTS)。OpenAI 适配器保留作为海外/降级后备。STT 由前端 Web Speech API 承担,后端 STT 仍是 `fake`。
```

Add a v0.2 entry to §9 changelog:

```markdown
| v0.2 | 2026-05-12 | 增加国产 AI 厂商支持(Qwen-VL / DeepSeek-V4 / MiniMax),关闭 §7.2 Q1 |
```

- [ ] **Step 2: Update `docs/plans/README.md`**

Add a Phase 6 row to the overview table:

```markdown
| 6 | 国产 AI 厂商接入 | 适配层 + 人物声音映射 | 不依赖 OpenAI 也能跑;持币人物有专属嗓音 | ⏳ 进行中:`2026-05-12-phase-6-domestic-providers.md` |
```

- [ ] **Step 3: Update `README.md`**

Update the provider/adapter matrix section to reflect the new providers. Sample row format:

```markdown
| Capability | Adapters available |
|---|---|
| Vision | `fake`, `openai` (gpt-4o), `qwen` (qwen-vl-max-latest, DashScope) |
| LLM    | `fake`, `openai` (gpt-4o-mini), `deepseek` (deepseek-v4-flash) |
| TTS    | `fake`, `openai` (tts-1-hd), `minimax` (speech-02-hd, 300+ voices) |
| STT    | `fake`, `openai` (whisper-1); frontend uses Web Speech API as primary |
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/plans/README.md docs/prd/2026-05-09-personalingualive-prd.md
git commit -m "docs: close PRD §7.2 Q1, document Phase 6 domestic providers"
```

### Task 6.6.5: End-to-end smoke check (manual)

- [ ] **Step 1: Create a local `.env` based on `.env.example`** filling in real keys:

```dotenv
PLL_AI_VISION_PROVIDER=qwen
PLL_AI_LLM_PROVIDER=deepseek
PLL_AI_TTS_PROVIDER=minimax
PLL_AI_STT_PROVIDER=fake

PLL_QWEN_API_KEY=<your-dashscope-key>
PLL_DEEPSEEK_API_KEY=<your-deepseek-key>
PLL_MINIMAX_API_KEY=<your-minimax-key>
PLL_MINIMAX_GROUP_ID=<your-minimax-group-id>
```

- [ ] **Step 2: Boot backend**

Run: `python -m uvicorn app.main:create_app --factory --reload`
Expected: starts without errors. `/healthz` returns 200.

- [ ] **Step 3: Boot frontend**

Run: `cd frontend && npm run dev`
Expected: opens at `http://localhost:5173`.

- [ ] **Step 4: Manual flow**

1. Upload a small kitchen photo.
2. Confirm Qwen returns hotspots (check backend logs for `qwen.vision.*`).
3. Click an object — persona card appears, `voice_id` is set.
4. Send a chat message — text streams from DeepSeek, audio plays via MiniMax. Backend logs show `deepseek.llm.*` and `minimax.tts.*`.
5. End session — `/api/chat/summary` returns a summary using DeepSeek.

If any step fails, note the failing log key and either fix the adapter or open a follow-up task — do not silently retry.

- [ ] **Step 5: Final commit if any tweaks emerged from smoke test**

```bash
git status
# review, then if changes:
git commit -am "fix: smoke-test tweaks for domestic provider e2e"
```

---

## Verification

| Check | Command | Expected |
|---|---|---|
| Backend unit tests | `pytest -q` | All previously passing tests still pass + ~25 new tests |
| Lint | `ruff check app tests` | No new warnings |
| Type check | `mypy app` | No new errors |
| Frontend tests | `cd frontend && npm test -- --run` | All tests pass |
| Frontend type check | `cd frontend && npx tsc --noEmit` | No errors |
| Smoke (manual) | Sub-phase 6.6.5 flow | Image → hotspots → chat → audio works end-to-end on domestic providers |

### Acceptance criteria

- `PLL_AI_VISION_PROVIDER=qwen` boots and analyzes a real photo.
- `PLL_AI_LLM_PROVIDER=deepseek` produces streaming chat responses with proper `<speak>/<learning>/<followup>` tagging.
- `PLL_AI_TTS_PROVIDER=minimax` returns playable mp3 audio.
- Different persona archetypes (cake / wrench / robot / pet) receive distinguishable voices — auditory verification by the user during smoke flow.
- OpenAI adapters still pass their existing tests (fallback path remains usable).
- `pytest -q` total count grows by ~25 tests; no existing tests skipped or removed.

---

## Self-review

**Spec coverage:**
- Vendor split (Qwen / DeepSeek / MiniMax) — covered by 6.2–6.4 and factory wiring 6.6.1–6.6.3.
- Persona character voices (PRD §4.5) — covered by 6.5.1 (voice_picker) + 6.5.2 (persona response) + 6.5.3 (orchestrator) + 6.5.4 (WS init) + 6.5.5 (frontend).
- OpenAI kept as fallback — factory branches additive, no deletions; existing OpenAI tests untouched.
- Settings + validators — 6.1 covers per-provider key requirements.
- Docs (PRD §7.2 closure, plans README, main README, .env.example) — covered by 6.1 + 6.6.4.

**Placeholder scan:** no "TBD" / "implement later" / "similar to" entries; every code step contains the actual code.

**Type consistency:**
- `pick_voice(voice_traits: dict | None) -> str` — same signature in test (Task 6.5.1) and consumer (Task 6.5.2).
- `MiniMaxTTSAdapter.__init__` kwargs (`api_key, group_id, base_url, model, default_voice, timeout_s`) — same set in test builder (Task 6.4.1), implementation (Task 6.4.2), and factory branch (Task 6.6.3).
- `chat_stream(..., voice_id: str | None = None)` — same signature in orchestrator (Task 6.5.3), WS test (Task 6.5.4), and `chat.py` callsite (Task 6.5.4).
- `_PROVIDER = "deepseek"` / `"qwen"` / `"minimax"` — matches the assertions on `exc.provider` in the adapter test files.

**Risks flagged for executor:**
- MiniMax voice IDs are a moving catalog — if a `pick_voice` mapping returns 404 at runtime, expand `_VOICE_TABLE` to the closest valid alternative rather than crashing. MiniMax adapter's `UpstreamFailureError` from `base_resp.status_code != 0` will surface this.
- DeepSeek SSE stream tested via batched response body, not true chunked transfer. This matches how `OpenAILLMAdapter`'s tests are structured; if real-network streaming behaves differently, integration tests in 6.6.5 will catch it.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-12-phase-6-domestic-providers.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per sub-phase (6.1 → 6.6), review between tasks, fast iteration. Best for keeping main context focused on the design while individual adapters are fleshed out.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch with checkpoints. Best if you want to watch each TDD cycle live.

Which approach?

