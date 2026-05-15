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
