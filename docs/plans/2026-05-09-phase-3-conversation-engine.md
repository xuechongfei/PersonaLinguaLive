# Phase 3: Conversation Engine (M4-M10) Implementation Plan

> **Status:** ✅ Complete — all 6 sub-phases finished
> **Commits:** `13c0081` .. `205b3f1` (13 commits)
> **Execution dates:** 2026-05-09 — 2026-05-10

**Goal:** Build the full conversational AI pipeline — from clicking an object in an image to having a voice conversation with its AI persona, with learning feedback and local storage.

**Architecture:** Three new adapter families (LLM, TTS, STT) following the existing VisionAdapter Protocol pattern. WebSocket-based real-time chat orchestration. In-memory context management. Frontend gets ChatPanel, PersonaMouth (lip-sync), MicButton (Web Speech API), IndexedDB persistence, and summary card.

**Tech Stack:** Backend: Python 3.12, FastAPI (WebSocket), httpx, structlog. Frontend: React 18, TypeScript 5, Tailwind 3, Web Audio API, Web Speech API, IndexedDB.

---

## Sub-phase 3.1: AI Adapter Protocols & Factory (Infrastructure)

### Task 3.1.1: LLMAdapter Protocol + Fake + OpenAI

**Files created:**
- `app/adapters/llm/__init__.py`
- `app/adapters/llm/base.py` — `LLMAdapter` Protocol: `generate()`, `generate_stream()` (AsyncGenerator of tokens)
- `app/adapters/llm/fake.py` — `FakeLLMAdapter`: deterministic JSON for persona, yields tokens for streaming
- `app/adapters/llm/openai_llm.py` — `OpenAILLMAdapter`: httpx POST to `/chat/completions`, streaming via SSE
- `tests/test_fake_llm_adapter.py`
- `tests/test_openai_llm_adapter.py` (respx-mocked)

**Commit:** `13c0081`

### Task 3.1.2: TTSAdapter Protocol + Fake + OpenAI

**Files created:**
- `app/adapters/tts/__init__.py`
- `app/adapters/tts/base.py` — `TTSAdapter` Protocol: `synthesize(text, voice) -> bytes`
- `app/adapters/tts/fake.py` — `FakeTTSAdapter`: returns minimal WAV bytes (44-byte header + 1 sample)
- `app/adapters/tts/openai_tts.py` — `OpenAITTSAdapter`: httpx POST to `/audio/speech`
- `tests/test_fake_tts_adapter.py`
- `tests/test_openai_tts_adapter.py` (respx-mocked)

### Task 3.1.3: STTAdapter Protocol + Fake + OpenAI

**Files created:**
- `app/adapters/stt/__init__.py`
- `app/adapters/stt/base.py` — `STTAdapter` Protocol: `transcribe(audio_bytes, language?) -> str`
- `app/adapters/stt/fake.py` — `FakeSTTAdapter`: trigger bytes return deterministic text (empty bytes → empty string, `pll_stt_test_` prefix → fixed text)
- `app/adapters/stt/openai_stt.py` — `OpenAISTTAdapter`: multipart POST to `/audio/transcriptions`
- `tests/test_fake_stt_adapter.py`
- `tests/test_openai_stt_adapter.py` (respx-mocked)

### Task 3.1.4: Factory wiring + Settings update

**Files modified:**
- `app/config.py` — Added LLM/TTS/STT provider settings (`ai_llm_provider`, `ai_tts_provider`, `ai_stt_provider`), model names (`openai_model_llm`, `openai_model_tts`, `openai_model_stt`), voice (`openai_tts_voice`), rate limits (`rate_limit_persona_per_min`, `rate_limit_chat_messages_per_min`)
- `app/adapters/factory.py` — Added `build_llm_adapter()`, `build_tts_adapter()`, `build_stt_adapter()`

**Files created:**
- `tests/test_llm_factory.py`
- `tests/test_tts_factory.py`
- `tests/test_stt_factory.py`

**Commit:** `3095c8e`

**Deviation from plan:** `.env.example` was updated later in Task 3.6.2 rather than here.

---

## Sub-phase 3.2: Backend Services

### Task 3.2.1: Persona generation prompt + schemas

**Files created:**
- `app/prompts/persona_gen.py` — `build_persona_messages()`: creates persona name, description, system_prompt from object + scene
- `app/schemas/persona.py` — `PersonaGenerateRequest`, `PersonaGenerateResponse` Pydantic models
- `tests/test_persona_prompt.py`

### Task 3.2.2: PersonaService with LRU cache

**Files created:**
- `app/services/persona_service.py` — `PersonaService`: takes LLMAdapter, builds prompt, caches via `OrderedDict` (max 100)
- `tests/test_persona_service.py`

### Task 3.2.3: Chat system prompt (3-segment M7) + schemas

**Files created:**
- `app/prompts/chat_system.py` — `build_chat_system_message()`: persona + user_level, instructs 3-segment format (`<speak>`/`<learning>`/`<followup>`)
- `app/schemas/chat.py` — `ChatSegment`, `ChatMessage`, `ChatTurn`, `ChatSummaryRequest/Response`
- `tests/test_chat_prompt.py`

**Commit (3.2.1-3.2.3):** `03d422d`

### Task 3.2.4: ContextManager

**Files created:**
- `app/services/context_manager.py` — `ContextManager`: per-session sliding window (10 exchanges = 20 messages), LLM summarization when full via `summarize()`, `add_turn()`, `get_context()`, `clear_session()`
- `tests/test_context_manager.py`

**Deviation from plan:** Default window is 10 exchanges (20 messages) vs. the PRD's 20 turns. `summarize()` inserted as system message prepended to context.

**Commit:** `7124e33`

### Task 3.2.5: ChatOrchestrator

**Files created:**
- `app/services/chat_orchestrator.py` — `ChatOrchestrator.__init__()` takes `LLMAdapter`, `TTSAdapter`, `ContextManager`. `chat_stream()` is an AsyncGenerator yielding `text_chunk`, `result`, `error` event dicts. Pipeline: get context → build messages → LLM `generate_stream()` → accumulate tokens → regex XML parse 3 segments → TTS `synthesize()` → base64 encode → yield `result` event.
- `tests/test_chat_orchestrator.py`

**Deviation from plan:** TTS synthesis happens once at the end of each turn (after full LLM response), not streamed interleaved. This is a simplification — the design doc describes "边出文本边喂 TTS" but it wasn't implemented in this phase.

**Commit:** `a43d15f`

---

## Sub-phase 3.3: Backend API Layer

### Task 3.3.1: Persona generation endpoint

**Files created:**
- `app/api/persona.py` — `POST /api/persona/generate`: JSON body of `PersonaGenerateRequest`, rate limiter (`settings.rate_limit_persona_per_min`)
- `tests/test_persona_endpoint.py`

**Files modified:**
- `app/main.py` — Registered persona router at `/api/persona`

**Commit:** `84dd1ff`

### Task 3.3.2: Chat WebSocket endpoint

**Files created:**
- `app/api/chat.py` — WebSocket `/api/chat`: accepts init frame → orchestrator loop → streams events (`text_chunk`, `result`, `error`). Shared singleton `_CONTEXT_MANAGER` and `_RATE_LIMITER`.
- `tests/test_chat_endpoint.py`

**Files modified:**
- `app/main.py` — Registered chat router at `/api/chat`

**Commit:** `1597850`

### Task 3.3.3: Summary endpoint (M10)

**Files created:**
- `app/prompts/chat_summary.py` — `build_summary_messages()`: system prompt extracting `new_words`, `grammar_points`, `fluency_score` (1-10), `strengths`, `areas_to_improve`
- `tests/test_chat_summary.py`

**Files modified:**
- `app/api/chat.py` — Added `POST /api/chat/summary` endpoint, reuses shared `_CONTEXT_MANAGER`

**Deviation from plan:** Summary endpoint uses the shared ContextManager singleton from chat.py (not a separate session store), and uses the same `build_llm_adapter()` rather than a dedicated summary adapter.

**Commit:** `dd0a8d1`

---

## Sub-phase 3.4: Frontend Chat Infrastructure

### Task 3.4.1: PersonaMouth SVG + lip-sync (M4)

**Files created:**
- `frontend/src/components/PersonaMouth.tsx` — SVG face (120x120 viewBox), Web Audio API `AnalyserNode.getByteFrequencyData()` drives mouth `ry` animation (range 4-16), CSS pulse fallback
- `frontend/src/components/PersonaMouth.test.tsx`

### Task 3.4.2: WebSocket ChatClient + API additions

**Files created:**
- `frontend/src/lib/chat.ts` — `ChatClient` class: WebSocket connection, exponential backoff reconnect (3x), event dispatch (`on`/`off`/`emit`), init frame protocol
- `frontend/src/__tests__/chat.test.ts`

**Files modified:**
- `frontend/src/lib/api.ts` — Added `generatePersona()`, `fetchSummary()`, `PersonaGenerateRequest/Response`, `ChatSummaryRequest/Response` types

### Task 3.4.3: ChatPanel + MicButton

**Files created:**
- `frontend/src/components/MicButton.tsx` — `webkitSpeechRecognition`, pulsing red dot (CSS `animate-pulse`), disabled fallback when unsupported
- `frontend/src/components/ChatPanel.tsx` — Message list, text input, MicButton, TTS Audio playback from base64, streaming text via `streamingText` state, PersonaMouth integration, LearningTip display, auto-scroll (`scrollIntoView`), `isStreaming`/`isSpeaking` states
- `frontend/src/components/ChatPanel.test.tsx`
- `frontend/src/__tests__/MicButton.test.tsx`

**Commit (3.4.1-3.4.3):** `ce51673`, `6bef4d5`, `b5c99f0`

---

## Sub-phase 3.5: Frontend Enhancements

### Task 3.5.1: LearningTip component (M7)

**Files created:**
- `frontend/src/components/LearningTip.tsx` — Collapsible card, `aria-expanded`, conditional rendering when both props empty
- `frontend/src/__tests__/LearningTip.test.tsx`

### Task 3.5.2: LevelSelector (M8)

**Files created:**
- `frontend/src/components/LevelSelector.tsx` — Segmented control with `role="radiogroup"`, `aria-checked`, Tailwind indigo-600 active state
- `frontend/src/__tests__/LevelSelector.test.tsx`

**Deviation from plan:** LevelSelector is created but NOT yet integrated into StudioPage or any settings UI. User level defaults to intermediate on the backend.

### Task 3.5.3: IndexedDB persistence (M9)

**Files created:**
- `frontend/src/lib/storage.ts` — Raw IndexedDB wrapper (no `idb` library), 3 object stores (`images`, `conversations` with keyPath `sessionId`, `preferences`). CRUD: `saveImage`, `getImage`, `getAllImageKeys`, `saveConversation`, `getConversation`, `getAllConversationIds`, `savePreference`, `getPreference`, `clearAll`, `clearStore`
- `frontend/src/__tests__/storage.test.ts`

**Deviation from plan:** Uses raw IndexedDB instead of the `idb` library. No `vocabulary` store (V2 reserved).

### Task 3.5.4: SummaryCard (M10)

**Files created:**
- `frontend/src/components/SummaryCard.tsx` — Modal dialog with score badge (color-coded: 1-3 red, 4-6 amber, 7-10 green), new word chips, grammar list, strengths/improvements, empty state
- `frontend/src/__tests__/SummaryCard.test.tsx`

**Commit (3.5.1-3.5.4):** `ce51673`

---

## Sub-phase 3.6: Integration & Polish

### Task 3.6.1: Wire StudioPage full flow

**Files modified:**
- `frontend/src/pages/StudioPage.tsx` — Full state machine: `idle` → `analyzing` → `ready` → `persona_loading` → `chatting` → `summary`. Integrates `ChatPanel`, `SummaryCard`, `ChatClient`, `generatePersona()`, `fetchSummary()`. Replaced `PersonaPlaceholderPanel` with real chat and summary flow.
- `frontend/src/pages/StudioPage.test.tsx` — 5 integration tests with module-level mocks for API, ChatClient, and child components

**Commit:** `205b3f1`

### Task 3.6.2: Docs + CI

**Files modified:**
- `.env.example` — Added `PLL_AI_LLM_PROVIDER`, `PLL_AI_TTS_PROVIDER`, `PLL_AI_STT_PROVIDER`, `PLL_OPENAI_MODEL_LLM`, `PLL_OPENAI_MODEL_TTS`, `PLL_OPENAI_MODEL_STT`, `PLL_OPENAI_TTS_VOICE`, `PLL_RATE_LIMIT_PERSONA_PER_MIN`, `PLL_RATE_LIMIT_CHAT_MESSAGES_PER_MIN`
- `README.md` — Added Phase 3 section documenting conversation engine features

**Commit:** `205b3f1`

---

## Verification Results

| Check | Result |
|-------|--------|
| `uv run pytest -v` | 150 passed |
| `uv run ruff check app tests` | Clean |
| `cd frontend && npm test -- --run` | 81 passed (19 test files) |
| `cd frontend && npx tsc --noEmit` | Clean |
| `cd frontend && npm run build` | 164 KB (gzip 53 KB) |

## Key Deviations from Original Design

1. **TTS streaming** — Design doc specifies "边出文本边喂 TTS" (interleaved LLM→TTS streaming). Current implementation waits for full LLM response before TTS synthesis. Acceptable for MVP but adds latency.
2. **LevelSelector** — Component exists but is not wired into any UI flow. User level defaults to intermediate.
3. **PersonaMouth placement** — Shown in ChatPanel header rather than overlaid on the image object bbox as specified in design doc.
4. **IndexedDB** — Uses raw IndexedDB API instead of the `idb` library specified in the design.
5. **No Zustand store** — Design doc specifies Zustand for state management; current implementation uses React state + refs.
6. **No `lib/audio/` or `lib/stt/` sub-modules** — Lip-sync logic is inline in PersonaMouth; STT is inline in MicButton.

## Files Changed Summary

**Backend — created:**
- `app/adapters/llm/base.py`, `app/adapters/llm/fake.py`, `app/adapters/llm/openai_llm.py`
- `app/adapters/tts/base.py`, `app/adapters/tts/fake.py`, `app/adapters/tts/openai_tts.py`
- `app/adapters/stt/base.py`, `app/adapters/stt/fake.py`, `app/adapters/stt/openai_stt.py`
- `app/api/persona.py`, `app/api/chat.py`
- `app/services/persona_service.py`, `app/services/context_manager.py`, `app/services/chat_orchestrator.py`
- `app/prompts/persona_gen.py`, `app/prompts/chat_system.py`, `app/prompts/chat_summary.py`
- `app/schemas/persona.py`, `app/schemas/chat.py`
- 15 test files

**Backend — modified:**
- `app/config.py`, `app/adapters/factory.py`, `app/main.py`

**Frontend — created:**
- `src/components/PersonaMouth.tsx`, `src/components/ChatPanel.tsx`, `src/components/MicButton.tsx`
- `src/components/LearningTip.tsx`, `src/components/LevelSelector.tsx`, `src/components/SummaryCard.tsx`
- `src/lib/chat.ts`, `src/lib/storage.ts`
- 7 test files

**Frontend — modified:**
- `src/lib/api.ts`, `src/pages/StudioPage.tsx`, `src/pages/StudioPage.test.tsx`

**Root — modified:**
- `.env.example`, `README.md`
