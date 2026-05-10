"""WebSocket /api/chat endpoint."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.adapters.factory import build_llm_adapter, build_tts_adapter
from app.config import Settings
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


_INSTANCE_COUNTER = 0  # For unique session_id generation in tests


@router.websocket("")
async def chat_websocket(websocket: WebSocket) -> None:
    """WebSocket chat endpoint.

    Protocol:
        1. Client sends init frame:
            {"type": "init", "session_id": str, "system_message": dict,
             "user_level": str (optional, default "beginner")}

        2. Client sends user messages:
            {"type": "user_message", "content": str}

        3. Server streams event frames:
            {"type": "text_chunk", "content": str}
            {"type": "result", "segments": {...}, "audio_base64": str}
            {"type": "error", "message": str}
    """
    await websocket.accept()

    session_id: str | None = None

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
        context_mgr = ContextManager(llm=llm)
        orchestrator = ChatOrchestrator(llm=llm, tts=tts, context=context_mgr)

        log.info("chat.session_start", session_id=session_id, user_level=user_level)

        # 2. Chat loop
        while True:
            data = await websocket.receive_json()
            if data.get("type") != "user_message":
                continue

            user_message: str = data["content"]
            if not user_message.strip():
                continue

            log.info("chat.user_message", session_id=session_id, length=len(user_message))

            async for event in orchestrator.chat_stream(session_id, user_message, system_message):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        log.info(
            "chat.disconnect",
            session_id=session_id if "session_id" in dir() else "unknown",
        )
    except Exception as exc:
        log.error("chat.error", error=str(exc))
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
