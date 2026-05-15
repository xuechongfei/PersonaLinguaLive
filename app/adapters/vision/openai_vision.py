"""OpenAI Chat Completions adapter for vision (safety + objects)."""
from __future__ import annotations

import base64
import json

import httpx
import structlog

from app.adapters.vision.base import VisionIntent
from app.errors import UpstreamFailureError, UpstreamTimeoutError
from app.prompts.vision_safety import build_vision_safety_messages
from app.schemas.vision import BBox, DetectedObject, Entity, VisionResult

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

        log.info("openai.vision.call", model=self._model, image_bytes=len(image_bytes))

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

        result = _payload_to_result(payload)
        log.info("openai.vision.ok", is_safe=result.is_safe, entities=len(result.entities),
                 raw_scene=result.raw_scene[:80] if result.raw_scene else "")
        return result


def _payload_to_result(payload: dict) -> VisionResult:
    is_safe = bool(payload.get("is_safe", False))
    reasons = list(payload.get("reject_reasons") or [])
    raw_scene = str(payload.get("raw_scene") or payload.get("scene_summary") or "")

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
        except (ValueError, TypeError):
            continue

    # Backward-compat: also parse legacy `objects` payload shape into DetectedObject[]
    raw_objects = payload.get("objects") or []
    objects: list[DetectedObject] = []
    for idx, raw in enumerate(raw_objects, start=1):
        bbox_arr = raw.get("bbox") or [0, 0, 0, 0]
        if len(bbox_arr) != 4:
            continue
        try:
            confidence_raw = raw.get("confidence")
            confidence = 0.5 if confidence_raw is None else max(0.0, min(1.0, float(confidence_raw)))
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
        scene_summary=raw_scene,  # backward compat
        raw_scene=raw_scene,
        objects=objects,
        entities=entities,
    )
