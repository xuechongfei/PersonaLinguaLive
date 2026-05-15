"""POST /api/persona/generate endpoint — DEPRECATED in v0.3."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/persona", tags=["persona"])


@router.post("/generate")
async def deprecated_persona_generate():
    return JSONResponse(
        status_code=410,
        content={
            "detail": "POST /api/persona/generate is deprecated in v0.3. "
                      "Personas are now generated as part of the SceneBible "
                      "process. Use POST /api/vision/analyze instead."
        },
    )
