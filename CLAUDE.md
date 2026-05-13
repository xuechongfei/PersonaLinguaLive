# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Backend
uv sync --extra dev                         # install deps
uv run uvicorn app.main:app --reload --port 8000
uv run pytest -v                            # all tests
uv run pytest tests/test_config.py -k "deepseek" -v  # single test
uv run ruff check app tests                 # lint
uv run ruff check --fix app tests           # auto-fix

# Frontend
cd frontend && npm install && npm run dev   # dev server (port 5173, proxies /api to :8000)
cd frontend && npm test -- --run            # tests (vitest)
cd frontend && npx tsc --noEmit             # type-check
```

## Architecture

**Backend (FastAPI):** `app/main.py` uses `create_app()` factory. API routes: WebSocket `/api/chat`, POST `/api/vision/analyze`, POST `/api/persona/generate`, POST `/api/chat/summary`.

**Provider adapter layer (`app/adapters/`):** Each AI capability has a `base.py` Protocol class. Real adapters implement it. `factory.py` picks the adapter based on `Settings.ai_*_provider` (Literal: `fake`/`openai`/`qwen`/`deepseek`/`minimax`). OpenAIChat-compatible providers (DeepSeek, Qwen-VL via DashScope compatible-mode) reuse the same SSE/JSON patterns. MiniMax TTS is the only non-OpenAI-compatible adapter — auth uses `GroupId` query param, response is JSON with hex-encoded audio.

**Config (`app/config.py`):** Single `Settings` class (pydantic-settings, env prefix `PLL_`). Each provider has its own API key, base URL, model, and timeout fields. `@model_validator` enforces per-provider credential requirements.

**Chat orchestration:** `ChatOrchestrator.chat_stream()` streams LLM tokens over WebSocket, parses `<speak>/<learning>/<followup>` XML, kicks off TTS in background via `asyncio.create_task` when `</speak>` closes. `voice_id` flows from persona generation → WS init frame → orchestrator → TTS adapter.

**Context management:** `ContextManager` holds sliding window of 10 turns per session, auto-summarizes via LLM when over limit. In-memory, not persisted (singleton per process, reset on `create_app()`).

**Frontend (React + Vite):** Single-page app with Zustand store (`frontend/src/lib/store.ts`) holding the discriminated-union `StudioStatus` state machine: `idle → analyzing → ready → persona_loading → chatting → summary`. The store also carries `file`, `imageSize`, `chatClient`, `analyserNode`, `level`. `ChatClient` (`frontend/src/lib/chat.ts`) is a thin wrapper around native `WebSocket` with typed event dispatching.

Key pages: `StudioPage` (main flow), `HomePage`, `HistoryPage`, `VocabPage`. Components follow `ComponentName.tsx` + `ComponentName.test.tsx` co-location pattern under `frontend/src/components/`.

**Persistence:** Frontend only — IndexedDB via `frontend/src/lib/storage.ts` (conversations, vocab, profile). No backend database.

**Persona voice mapping:** `app/services/voice_picker.py` maps LLM-emitted `voice_traits` (`{gender, age, tone}`) to MiniMax voice IDs with 3-level fallback. `PersonaGenerateResponse.voice_id` carries this to the frontend, which sends it in the WS init frame.

## Tests

Tests use `respx` for HTTP mocking (backend) and `vitest` + `@testing-library/react` (frontend). `tests/conftest.py` auto-clears `PLL_*` env vars between tests. Fake adapters are the default; tests that need real adapter behavior mock at the HTTP layer with respx.

When adding a new adapter, follow the test pattern in `tests/test_openai_llm_adapter.py` / `test_openai_vision_adapter.py` / `test_openai_tts_adapter.py`: one test per HTTP code path, capture auth/model in request, verify error `.provider` assertion on raised exceptions.

## Commit convention

Conventional commits in English: `feat(scope):`, `fix(scope):`, `test(scope):`, `docs:`, `style:`. Committed directly to `master` (no feature branches per project convention).
