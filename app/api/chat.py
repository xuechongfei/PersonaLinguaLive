"""WebSocket /api/chat endpoint and POST /api/chat/summary."""
from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

from app.adapters.factory import build_llm_adapter, build_tts_adapter
from app.config import Settings, get_settings
from app.errors import RateLimitedError, WorldNotFoundError
from app.prompts.chat_summary import build_summary_messages
from app.prompts.learner_context import build_learner_context_message
from app.schemas.chat import ChatSummaryRequest, ChatSummaryResponse
from app.services.ambient_scheduler import AmbientScheduler
from app.services.chat_orchestrator import ChatOrchestrator
from app.services.context_manager import ContextManager
from app.utils.ratelimit import MemoryRateLimiter

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = structlog.get_logger("pll.chat")

# 单实例进程内的限流器。create_app() 启动时按 settings 重建。
_RATE_LIMITER: MemoryRateLimiter | None = None


def _ensure_limiter(settings: Settings) -> MemoryRateLimiter:
    global _RATE_LIMITER
    if _RATE_LIMITER is None:
        _RATE_LIMITER = MemoryRateLimiter(
            max_per_window=settings.rate_limit_chat_messages_per_min,
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


# 单实例进程内的上下文管理器。create_app() 启动时按 settings 重建。
_CONTEXT_MANAGER: ContextManager | None = None


def _ensure_context_manager(settings: Settings) -> ContextManager:
    global _CONTEXT_MANAGER
    if _CONTEXT_MANAGER is None:
        llm = build_llm_adapter(settings)
        _CONTEXT_MANAGER = ContextManager(llm=llm)
    return _CONTEXT_MANAGER


def reset_context_manager() -> None:
    """For tests: drop the singleton between create_app() calls."""
    global _CONTEXT_MANAGER
    _CONTEXT_MANAGER = None


_INSTANCE_COUNTER = 0  # For unique session_id generation in tests


@router.websocket("")
async def chat_websocket(websocket: WebSocket) -> None:
    """WebSocket chat endpoint.

    Protocol:
        1. Client sends init frame:
            {"type": "init", "session_id": str, "system_message": dict,
             "user_level": str (optional, default "beginner"),
             "learner_context": {"level": str, "recent_vocab": list[str],
                                  "weak_areas": list[str]} (optional),
             "world_id": str (optional),
             "npc_id": str (optional)}

        2. Client sends user messages:
            {"type": "user_message", "content": str}

        3. Server streams event frames:
            {"type": "text_chunk", "content": str}
            {"type": "speak_text", "content": str}     # emitted once </speak> closes
            {"type": "audio", "audio_base64": str}     # emitted as soon as TTS done
            {"type": "result", "segments": {...}, "audio_base64": str}
            {"type": "ambient", ...}                    # ambient NPC events
            {"type": "error", "message": str}
    """
    await websocket.accept()

    session_id: str | None = None
    ambient_task: asyncio.Task | None = None

    try:
        # 1. Receive init frame
        init_data = await websocket.receive_json()
        if init_data.get("type") != "init":
            await websocket.send_json({"type": "error", "message": "First message must be init"})
            await websocket.close()
            return

        session_id = init_data["session_id"]
        system_message: dict = init_data["system_message"]
        user_level: str = init_data.get("user_level", "beginner")
        learner_context_raw = init_data.get("learner_context") or {}
        voice_id: str | None = init_data.get("voice_id")
        world_id: str = init_data.get("world_id", "")
        npc_id: str = init_data.get("npc_id", "")
        learner_context_message = build_learner_context_message(
            level=learner_context_raw.get("level") or user_level,
            recent_vocab=learner_context_raw.get("recent_vocab"),
            weak_areas=learner_context_raw.get("weak_areas"),
        )

        settings = Settings()

        # Rate limit check on session
        limiter = _ensure_limiter(settings)
        ok, retry_after = limiter.check(session_id)
        if not ok:
            await websocket.send_json(
                {"type": "error", "message": f"Rate limited, retry after {retry_after}s"}
            )
            await websocket.close()
            return

        # Build dependencies
        llm = build_llm_adapter(settings)
        tts = build_tts_adapter(settings)
        context_mgr = _ensure_context_manager(settings)
        orchestrator = ChatOrchestrator(llm=llm, tts=tts, context=context_mgr)

        # Look up scene bible if world_id is provided
        scene_bible = None
        world_store = getattr(websocket.app.state, "world_store", None)
        if world_id and world_store:
            try:
                scene_bible = world_store.get_or_raise(world_id)
            except WorldNotFoundError:
                pass

        # Start ambient scheduler if we have a scene bible with NPCs
        ambient_queue: asyncio.Queue = asyncio.Queue()
        ambient_task: asyncio.Task | None = None
        if scene_bible is not None and len(scene_bible.npcs) > 1:
            scheduler = AmbientScheduler(llm=llm, bible=scene_bible)

            async def ambient_sender():
                await scheduler.run(
                    active_npc_id=npc_id,
                    is_streaming=lambda: context_mgr.is_streaming((session_id, npc_id) if npc_id else session_id),
                    ws_send=ambient_queue.put,
                )

            ambient_task = asyncio.create_task(ambient_sender())

        log.info("chat.session_start", session_id=session_id, user_level=user_level,
                 world_id=world_id, npc_id=npc_id)

        # 2. Chat loop — handles user messages AND ambient events
        async def _receive_ws():
            """Receive a user message from the WS and put it on an internal queue."""
            data = await websocket.receive_json()
            return ("ws", data)

        async def _receive_ambient():
            """Receive an ambient event from the scheduler queue."""
            event = await ambient_queue.get()
            return ("ambient", event)

        while True:
            # Wait for either a user message or an ambient event
            pending = [asyncio.create_task(_receive_ws())]
            if ambient_task is not None:
                pending.append(asyncio.create_task(_receive_ambient()))

            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

            source, data = next(iter(done)).result()

            if source == "ambient":
                # Send ambient event to client
                await websocket.send_json({"type": "ambient", **data})
                continue

            # source == "ws": user message
            if data.get("type") != "user_message":
                continue

            user_message: str = data["content"]
            if not user_message.strip():
                continue

            log.info("chat.user_message", session_id=session_id, length=len(user_message))

            async for event in orchestrator.chat_stream(
                session_id,
                user_message,
                system_message,
                learner_context_message=learner_context_message,
                voice_id=voice_id,
                scene_bible=scene_bible,
                npc_id=npc_id,
            ):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        log.info("chat.disconnect", session_id=session_id or "unknown")
    except Exception as exc:
        log.error("chat.error", error=str(exc))
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if ambient_task is not None:
            ambient_task.cancel()


@router.post("/summary", response_model=ChatSummaryResponse)
async def chat_summary(
    request: Request,
    body: ChatSummaryRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ChatSummaryResponse:
    """POST /api/chat/summary -- Generate learning summary from a session."""
    # Rate limit
    limiter = _ensure_limiter(settings)
    ok, retry_after = limiter.check(_client_ip(request))
    if not ok:
        raise RateLimitedError(retry_after_s=retry_after)

    # Get conversation context from shared ContextManager
    context_mgr = _ensure_context_manager(settings)
    context = context_mgr.get_context(body.session_id)

    # If no conversation found, return empty summary
    if not context:
        log.info("summary.no_session", session_id=body.session_id)
        return ChatSummaryResponse()

    # Build conversation text for summary
    conversation_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in context
    )

    # Call LLM for summary
    llm = build_llm_adapter(settings)
    messages = build_summary_messages(conversation_text, body.user_level)

    try:
        raw = await llm.generate(messages, temperature=0.3)
        data = json.loads(raw)
        result = ChatSummaryResponse(
            new_words=data.get("new_words", []),
            grammar_points=data.get("grammar_points", []),
            fluency_score=data.get("fluency_score", 5),
            strengths=data.get("strengths", []),
            areas_to_improve=data.get("areas_to_improve", []),
        )
    except (json.JSONDecodeError, KeyError) as exc:
        log.warning("summary.parse_error", session_id=body.session_id, error=str(exc))
        result = ChatSummaryResponse()

    log.info("summary.ok", session_id=body.session_id, fluency_score=result.fluency_score)
    return result
