# Phase 4: Adaptive Coach — Personalized Learning & Live Latency

> **Status:** ✅ Completed
> **Planned date:** 2026-05-11
> **Executed date:** 2026-05-11
> **PRD reference:** `docs/prd/2026-05-09-personalingualive-prd.md` v0.1 (V2 modules)
> **Design reference:** `docs/design/2026-05-09-personalingualive-design.md` v0.1

## Execution summary

| Sub-phase | Outcome |
|---|---|
| 4.1 Learner Profile & Level Wiring | `loadProfile` / `saveProfile` over `preferences` store; `LevelSelector` rendered on upload screen; level threads through `client.connect()` and `generatePersona`. |
| 4.2 Conversation & Image Persistence | `conversationRef` accumulates turns and writes on every `handleTurnComplete`; `saveImage(sessionId, file)` on persona create; new `#/history` route lists past sessions and reopens their `SummaryCard`. |
| 4.3 Vocabulary Notebook (SRS-lite) | `DB_VERSION` bumped to 2 with new `vocabulary` store; pure `nextSchedule()` SM2-lite; `SummaryCard` auto-saves words; `#/vocab` route with All / Review tabs and Again / Hard / Good / Easy grading. |
| 4.4 Adaptive Prompt Injection | `build_learner_context_message` produces a system-role message prepended to the LLM message list; `collectLearnerContext()` reads recent 20 vocab + last summary `areasToImprove`; threaded through the WS init frame. |
| 4.5 Interleaved TTS Streaming | `ChatOrchestrator` fires TTS via `asyncio.create_task` the moment `</speak>` closes; emits `speak_text` → `audio` → `result` so the client can start playback before the LLM stream finishes. |
| 4.6 Integration & Polish | `ChatPanel` owns a lazy `AudioContext + AnalyserNode`, routes the played `<audio>` through Web Audio so `PersonaMouth` lip-syncs from real amplitude; README + roadmap updated. |

**Final verification (2026-05-11):**

- Backend `uv run pytest -q`: **157 passed**
- Backend `uv run ruff check app tests`: clean
- Frontend `npm test -- --run`: **101 passed across 23 files**
- Frontend `npx tsc --noEmit`: clean
- Frontend `npm run build`: **178.69 KB / 56.60 KB gz** (budget 220 / 70)

---

## Context

Phase 3 landed a working voice-chat pipeline: upload → analyze → pick object → talk with persona → summary. But the experience is generic and stateless:

- **No learner profile.** `LevelSelector` was built (`frontend/src/components/LevelSelector.tsx:1-43`) but never rendered. Every session defaults to "beginner" via `ChatClient.connect` (`frontend/src/lib/chat.ts:23,47`); the level the user picks is invisible to the LLM prompt at `app/prompts/chat_system.py:5-45`.
- **No persistence.** `storage.ts` (`frontend/src/lib/storage.ts:1-138`) implements `images` / `conversations` / `preferences` stores, but `StudioPage` never calls any of them — close the tab and the session is gone.
- **No vocabulary memory.** `SummaryCard` shows `new_words` once and discards them. The design doc reserved a `vocabulary` IndexedDB store that was never created.
- **First-audio latency is poor.** `ChatOrchestrator.chat_stream` (`app/services/chat_orchestrator.py:54-85`) finishes the entire LLM stream, then runs TTS, then emits one `result` event. The user waits ~1s+ after the typewriter finishes before hearing anything. The design always intended interleaved TTS.

**Phase 4 outcome:** the app *knows the user* and *responds faster*. We wire the dormant LevelSelector, persist conversations and preferences locally, build a personal vocabulary notebook with light spaced-repetition review, inject learner history into prompts so the LLM adapts, and refactor the orchestrator to start TTS as soon as `</speak>` closes — turning ~1s of dead air into near-zero perceived latency.

---

## Goals

1. Persist per-user state in IndexedDB and rehydrate on app load.
2. Wire `LevelSelector` end-to-end (UI → ChatClient → WS init → system prompt).
3. Save every finished conversation; let the user browse past sessions.
4. New vocabulary notebook: capture words from `SummaryCard`, review them with SM2-lite.
5. Inject "what the learner has been learning" into the persona system prompt so personas recycle vocab and stay calibrated to level.
6. Cut first-audio latency by streaming TTS for the `<speak>` segment as soon as it closes.

Non-goals (defer to Phase 5): cross-device sync, server-side learner profiles, account/auth, multilingual targets other than English, phoneme-level pronunciation scoring.

---

## Sub-phase 4.1 — Learner Profile & Level Wiring

**Files created**
- `frontend/src/lib/profile.ts` — `LearnerProfile` type `{ level: UserLevel, createdAt, updatedAt }`; `loadProfile()` / `saveProfile()` backed by `savePreference('profile', ...)` from `frontend/src/lib/storage.ts:100-118`.
- `frontend/src/lib/profile.test.ts`

**Files modified**
- `frontend/src/pages/StudioPage.tsx:22-28` — load profile on mount via `useEffect`; render `<LevelSelector>` (`frontend/src/components/LevelSelector.tsx`) in the upload / ready state; persist level on change.
- `frontend/src/pages/StudioPage.tsx:58-61` — pass `profile.level` as the third arg to `client.connect()` (already supported at `frontend/src/lib/chat.ts:47`).
- `frontend/src/pages/StudioPage.tsx:46-51` — pass `user_level: profile.level` to `generatePersona()` (already in request schema at `frontend/src/lib/api.ts:115-119`).
- `app/prompts/chat_system.py:5-45` — verify `user_level` flows through (it already does); no change expected.

**Verification:** Pick "Advanced" in the UI, refresh page, level should still be "Advanced". Start a chat — persona system prompt at `app/prompts/chat_system.py:26-31` should contain the advanced-level instruction string.

---

## Sub-phase 4.2 — Conversation & Image Persistence

**Files modified**
- `frontend/src/components/ChatPanel.tsx:48-78` — inside `handleResult`, append a turn `{userMessage, assistantResponse, timestamp}` to local state and pass them up via a new `onTurnComplete` prop.
- `frontend/src/pages/StudioPage.tsx`:
  - Pass `onTurnComplete={handleTurn}` to `<ChatPanel>`; inside `handleTurn`, call `saveConversation` (`frontend/src/lib/storage.ts:69-77`) with the running `ConversationData` (shape already defined at `frontend/src/lib/storage.ts:1-12`).
  - On `handleSelectObject` success, call `saveImage(sessionId, file)` (`frontend/src/lib/storage.ts:38-46`) using the compressed `file` from state.

**Files created**
- `frontend/src/pages/HistoryPage.tsx` — list past sessions via `getAllConversationIds` (`frontend/src/lib/storage.ts:89-97`) + `getConversation`; each row shows persona name, date, fluency score (if saved); click opens a read-only `SummaryCard`. Reuses `frontend/src/components/SummaryCard.tsx` in a non-interactive mode.
- `frontend/src/pages/HistoryPage.test.tsx`

**Files modified**
- `frontend/src/App.tsx` — extend the hash router with a `#history` route.
- `frontend/src/pages/HomePage.tsx:14-20` — add "History" + "Vocabulary" secondary buttons under the main CTA.

**Persistence shape extension:** Extend `ConversationData` at `frontend/src/lib/storage.ts:1-12` with optional `summary?: ChatSummaryResponse` so the History view can render saved summaries without re-querying the LLM.

**Verification:** Finish a session → reload tab → open `#history` → previous session is visible and clicking it reopens its summary modal.

---

## Sub-phase 4.3 — Vocabulary Notebook (SRS-lite)

**Files modified**
- `frontend/src/lib/storage.ts:14-35` — bump `DB_VERSION` to 2; add `vocabulary` store (keyPath `word`) in `onupgradeneeded`. New helpers: `saveWord(entry)`, `getAllWords()`, `getDueWords(now)`, `markReviewed(word, quality)`. Entry shape: `{ word, definition, exampleSentence, sessionId, addedAt, dueAt, ease, intervalDays, reps }`.
- `app/prompts/chat_summary.py:14-23` — extend the LLM output schema to return `new_words` as objects: `[{ word, definition, example }]` instead of bare strings.
- `app/schemas/chat.py:24-29` — change `new_words: list[str]` → `new_words: list[VocabEntry]` with a new `VocabEntry` model; keep `list[str]` accepted via a `field_validator` for backwards-compat with already-saved sessions.
- `frontend/src/lib/api.ts:165-170` — mirror the schema change.
- `frontend/src/components/SummaryCard.tsx` — render the richer entries; auto-call `saveWord` for each on first render (idempotent via keyPath).

**Files created**
- `frontend/src/pages/VocabPage.tsx` — two tabs: "All words" (sorted by `addedAt`) and "Review" (filters `getDueWords(Date.now())`; quality buttons 1–4 drive SM2-lite update).
- `frontend/src/lib/srs.ts` — pure SM2-lite update: `nextSchedule(entry, quality) → { ease, intervalDays, dueAt, reps }`.
- `frontend/src/lib/srs.test.ts`
- `frontend/src/pages/VocabPage.test.tsx`

**Files modified**
- `frontend/src/App.tsx` — add `#vocab` route.

**Verification:** Finish a session whose summary contains words → open `#vocab` → words appear in "All words". Open "Review", grade a card "Easy" → its `dueAt` shifts forward and disappears from due list.

---

## Sub-phase 4.4 — Adaptive Prompt Injection

**Files created**
- `app/prompts/learner_context.py` — `build_learner_context_message(level, recent_vocab[], weak_areas[])` returns a system-role dict like `"The learner is at <level>. Recently learned: X, Y, Z. They struggle with: <areas>. Recycle their vocab when natural; avoid jargon they haven't seen."`
- `tests/test_learner_context_prompt.py`
- `frontend/src/lib/learnerContext.ts` — `collectLearnerContext()` reads from `storage.ts`: most recent 20 vocab words (`getAllWords` sorted desc by `addedAt`), `areas_to_improve` from the latest saved `ConversationData.summary`.

**Files modified**
- `app/api/chat.py:92-100` — accept optional `learner_context: dict` on the init frame (`{level, recent_vocab, weak_areas}`); pass through to orchestrator.
- `app/services/chat_orchestrator.py:27-32,54-59` — accept optional `learner_context_message` parameter; if present, prepend it to `messages` before the persona system message.
- `frontend/src/lib/chat.ts:47-69` — extend `connect()` signature to accept `learnerContext?: LearnerContext`; include it in the init frame.
- `frontend/src/pages/StudioPage.tsx:56-61` — call `collectLearnerContext()` before `client.connect`, pass it in.
- `tests/test_chat_orchestrator.py` — assert learner context message is the first message when provided.

**Verification:** Save several words → start a new chat → backend logs (`app/api/chat.py:120`) show the learner context; the persona references at least one prior word within 3 turns (fake LLM scripted to echo a learner-context word; OpenAI behavior verified manually).

---

## Sub-phase 4.5 — Interleaved TTS Streaming

**Files modified**
- `app/services/chat_orchestrator.py:54-85` — refactor `chat_stream`:
  - While accumulating tokens, scan `full_response` for `</speak>`; the first time it appears, extract the speak segment, spawn `asyncio.create_task(self._tts.synthesize(speak_text, voice="alloy"))`, and emit `{"type": "speak_text", "content": speak_text}`.
  - Keep yielding `text_chunk` events for the remaining `<learning>` / `<followup>` content.
  - After LLM stream ends, `await` the TTS task and emit `{"type": "audio", "audio_base64": ...}` as a standalone event.
  - Final `result` event no longer carries audio; it only carries parsed `segments`. (Backward-compat shim: still include `audio_base64` for one minor version so older clients keep working.)
- `app/api/chat.py` — no change; events flow through verbatim.
- `frontend/src/lib/chat.ts:3-11` — add `'speak_text' | 'audio'` to `ChatEventType`.
- `frontend/src/components/ChatPanel.tsx:40-78` — handle `audio` event: start playback immediately, set `isSpeaking=true`, wire `AnalyserNode` from a single `AudioContext` (created lazily, persisted in a ref) so `PersonaMouth` (`frontend/src/components/PersonaMouth.tsx`) lip-syncs. Handle `speak_text` to commit the speak message before learning/followup arrive.
- `tests/test_chat_orchestrator.py` — new test asserting `audio` event arrives before `result` when speak segment closes mid-stream (use a fake LLM that yields tokens with a delay after `</speak>`).
- `tests/test_chat_websocket.py` (if exists; otherwise extend) — assert frame ordering.
- `frontend/src/components/ChatPanel.test.tsx` (if exists; otherwise create) — assert audio plays on `audio` event without waiting for `result`.

**Concurrency note:** `asyncio.create_task` is safe inside the async generator because we still `await` the task before yielding the final event; no orphaned coroutines.

**Verification:** With fake adapters configured to add a 500ms delay per token after `</speak>`, the first `audio` event should arrive before the final `result` event. Manually: send a message, audio should begin playing while text is still typing the followup.

---

## Sub-phase 4.6 — Integration & Polish

**Files modified**
- `frontend/src/pages/StudioPage.tsx` — pass the lazily-created `AnalyserNode` ref into `<ChatPanel analyserNode={...}>` so `PersonaMouth` reacts to real audio amplitude (currently always `undefined` per `frontend/src/components/ChatPanel.tsx:22`).
- `.env.example` — document any new settings (none expected unless we expose SRS interval defaults).
- `README.md` — append a "Phase 4" section describing learner profile, history, vocab, adaptive prompts, low-latency audio.
- `docs/plans/README.md` — mark Phase 4 complete in the roadmap table (during execution, not now).

---

## Critical Files Touched (Cheat Sheet)

**Backend**
- `app/services/chat_orchestrator.py` — interleaved TTS refactor
- `app/api/chat.py` — accept `learner_context` on init
- `app/prompts/learner_context.py` — NEW
- `app/prompts/chat_summary.py` — return word definitions
- `app/schemas/chat.py` — `VocabEntry` type

**Frontend**
- `frontend/src/pages/StudioPage.tsx` — main integration site
- `frontend/src/pages/VocabPage.tsx` — NEW
- `frontend/src/pages/HistoryPage.tsx` — NEW
- `frontend/src/lib/storage.ts` — DB v2 migration + `vocabulary` store
- `frontend/src/lib/profile.ts` — NEW
- `frontend/src/lib/learnerContext.ts` — NEW
- `frontend/src/lib/srs.ts` — NEW
- `frontend/src/lib/chat.ts` — `audio` / `speak_text` events
- `frontend/src/components/ChatPanel.tsx` — early audio playback, AnalyserNode wiring
- `frontend/src/components/SummaryCard.tsx` — render rich vocab, save on render
- `frontend/src/App.tsx` — `#vocab`, `#history` routes

---

## Verification

| Check | Command |
|---|---|
| Backend tests | `uv run pytest -v` (target: existing 150 + ~15 new pass) |
| Backend lint | `uv run ruff check app tests` |
| Frontend tests | `cd frontend && npm test -- --run` (target: existing 81 + ~25 new pass) |
| TypeScript | `cd frontend && npx tsc --noEmit` |
| Build size | `cd frontend && npm run build` (budget: ≤ 220 KB / 70 KB gz) |

**E2E manual flow:**
1. Fresh DB (`indexedDB` purged in DevTools) → open app → HomePage shows History/Vocab links → both empty.
2. Pick "Intermediate" in LevelSelector → upload an image → start a chat.
3. Mid-LLM-stream: audio begins playing before final result event lands (verify in Network → WS frames: `audio` arrives before `result`).
4. Send 3 messages → End Chat → SummaryCard shows enriched words.
5. Close SummaryCard → reload tab → History page shows the session; clicking it reopens its summary.
6. Open Vocab page → "All words" lists saved words → switch to "Review" → grade one card "Easy" → its `dueAt` advances; refresh → grading persisted.
7. Start a second chat → backend log line `chat.session_start` should now also log non-empty `learner_context`; persona should naturally use one of the saved words within a few turns.

---

## Out of Scope (deferred to Phase 5+)

- Multi-persona simultaneous chat (PRD V3)
- Pronunciation scoring (needs phoneme-timestamp STT adapter)
- Cross-device profile sync, account system
- Server-side vocabulary store (Phase 4 stays client-only per Phase 3's "client-heavy state" decision)
- Replacing React `useState`/`useRef` with Zustand (still a known deviation; not blocking)
- `PersonaMouth` overlay on object bbox (visual polish; deferred)
