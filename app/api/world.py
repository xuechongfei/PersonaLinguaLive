"""SSE endpoint for world asset streaming."""
from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.status import HTTP_404_NOT_FOUND

from app.errors import WorldNotFoundError
from app.schemas.world import WorldAssets
from app.services.world_store import WorldStore

log = structlog.get_logger("pll.world")
router = APIRouter(prefix="/world", tags=["world"])


def _get_world_store(request: Request) -> WorldStore:
    return request.app.state.world_store


@router.get("/{world_id}")
async def get_world_stream(world_id: str, request: Request):
    """SSE endpoint that streams world assets as they become available."""
    store: WorldStore = _get_world_store(request)

    # Validate exists
    try:
        store.get_or_raise(world_id)
    except WorldNotFoundError:
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
        for _ in range(600):  # 600 * 0.5s = 300s max wait (5 min for slow imagegen)
            state = store.get_state(world_id)
            if state == "world_ready":
                log.info("world.sse.ready", world_id=world_id)
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
                yield 'event: error\ndata: {"message":"generation failed"}\n\n'
                return
            await asyncio.sleep(0.5)
        yield 'event: error\ndata: {"message":"timeout waiting for world assets"}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _asset_to_events(assets: WorldAssets):
    yield f"event: background_ready\ndata: {json.dumps({'image_base64': assets.background_base64})}\n\n"
    for sprite in assets.sprites:
        yield f"event: npc_sprite_ready\ndata: {sprite.model_dump_json()}\n\n"
