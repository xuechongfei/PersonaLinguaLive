"""voice_picker: map persona voice_traits dict to a MiniMax voice_id."""
from __future__ import annotations

FALLBACK_VOICE = "English_expressive_narrator"

_VOICE_TABLE: dict[tuple[str, str, str], str] = {
    ("female", "adult", "warm"):     "English_friendly_female",
    ("female", "adult", "sweet"):    "English_sweet_female",
    ("female", "adult", "confident"):"English_confident_female",
    ("female", "adult", "neutral"):  "English_calm_female",
    ("female", "adult", "playful"):  "English_playful_female",
    ("male", "adult", "warm"):       "English_friendly_male",
    ("male", "adult", "gruff"):      "English_deep_male",
    ("male", "adult", "confident"):  "English_confident_male",
    ("male", "adult", "neutral"):    "English_calm_male",
    ("male", "adult", "playful"):    "English_cheerful_male",
    ("female", "child", "playful"):  "English_young_girl",
    ("female", "child", "sweet"):    "English_young_girl",
    ("male", "child", "playful"):    "English_young_boy",
    ("female", "elder", "warm"):     "English_wise_grandma",
    ("male", "elder", "gruff"):      "English_wise_grandpa",
}

_GENDER_AGE_DEFAULTS: dict[tuple[str, str], str] = {
    ("female", "adult"): "English_friendly_female",
    ("male", "adult"): "English_friendly_male",
    ("female", "child"): "English_young_girl",
    ("male", "child"): "English_young_boy",
    ("female", "elder"): "English_wise_grandma",
    ("male", "elder"): "English_wise_grandpa",
}

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
