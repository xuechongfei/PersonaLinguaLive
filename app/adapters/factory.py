"""Provider factories: pick adapter based on settings."""
from __future__ import annotations

from app.adapters.llm.base import LLMAdapter
from app.adapters.llm.fake import FakeLLMAdapter
from app.adapters.llm.deepseek_llm import DeepSeekLLMAdapter
from app.adapters.llm.openai_llm import OpenAILLMAdapter
from app.adapters.stt.base import STTAdapter
from app.adapters.stt.fake import FakeSTTAdapter
from app.adapters.stt.openai_stt import OpenAISTTAdapter
from app.adapters.tts.base import TTSAdapter
from app.adapters.tts.fake import FakeTTSAdapter
from app.adapters.tts.minimax_tts import MiniMaxTTSAdapter
from app.adapters.tts.openai_tts import OpenAITTSAdapter
from app.adapters.vision.base import VisionAdapter
from app.adapters.vision.fake import FakeVisionAdapter
from app.adapters.vision.openai_vision import OpenAIVisionAdapter
from app.adapters.vision.qwen_vision import QwenVisionAdapter
from app.config import Settings


def build_vision_adapter(settings: Settings) -> VisionAdapter:
    if settings.ai_vision_provider == "fake":
        return FakeVisionAdapter()
    if settings.ai_vision_provider == "openai":
        _require_api_key(settings)
        return OpenAIVisionAdapter(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            model=settings.openai_model_vision,
            timeout_s=settings.openai_request_timeout_s,
        )
    if settings.ai_vision_provider == "qwen":
        if settings.qwen_api_key is None:
            raise RuntimeError("qwen provider selected but PLL_QWEN_API_KEY is missing")
        return QwenVisionAdapter(
            api_key=settings.qwen_api_key.get_secret_value(),
            base_url=settings.qwen_base_url,
            model=settings.qwen_model_vision,
            timeout_s=settings.qwen_request_timeout_s,
        )
    raise RuntimeError(f"unknown vision provider: {settings.ai_vision_provider}")


def build_llm_adapter(settings: Settings) -> LLMAdapter:
    if settings.ai_llm_provider == "fake":
        return FakeLLMAdapter()
    if settings.ai_llm_provider == "openai":
        _require_api_key(settings)
        return OpenAILLMAdapter(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            model=settings.openai_model_llm,
            timeout_s=settings.openai_request_timeout_s,
        )
    if settings.ai_llm_provider == "deepseek":
        if settings.deepseek_api_key is None:
            raise RuntimeError("deepseek provider selected but PLL_DEEPSEEK_API_KEY is missing")
        return DeepSeekLLMAdapter(
            api_key=settings.deepseek_api_key.get_secret_value(),
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model_llm,
            timeout_s=settings.deepseek_request_timeout_s,
        )
    raise RuntimeError(f"unknown LLM provider: {settings.ai_llm_provider}")


def build_tts_adapter(settings: Settings) -> TTSAdapter:
    if settings.ai_tts_provider == "fake":
        return FakeTTSAdapter()
    if settings.ai_tts_provider == "openai":
        _require_api_key(settings)
        return OpenAITTSAdapter(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            model=settings.openai_model_tts,
            timeout_s=settings.openai_request_timeout_s,
        )
    if settings.ai_tts_provider == "minimax":
        if settings.minimax_api_key is None or not settings.minimax_group_id:
            raise RuntimeError(
                "minimax provider selected but PLL_MINIMAX_API_KEY / PLL_MINIMAX_GROUP_ID is missing"
            )
        return MiniMaxTTSAdapter(
            api_key=settings.minimax_api_key.get_secret_value(),
            group_id=settings.minimax_group_id,
            base_url=settings.minimax_base_url,
            model=settings.minimax_model_tts,
            default_voice=settings.minimax_default_voice,
            timeout_s=settings.minimax_request_timeout_s,
        )
    raise RuntimeError(f"unknown TTS provider: {settings.ai_tts_provider}")


def build_stt_adapter(settings: Settings) -> STTAdapter:
    if settings.ai_stt_provider == "fake":
        return FakeSTTAdapter()
    if settings.ai_stt_provider == "openai":
        _require_api_key(settings)
        return OpenAISTTAdapter(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            model=settings.openai_model_stt,
            timeout_s=settings.openai_request_timeout_s,
        )
    raise RuntimeError(f"unknown STT provider: {settings.ai_stt_provider}")


def _require_api_key(settings: Settings) -> None:
    if settings.openai_api_key is None:
        raise RuntimeError("openai provider selected but PLL_OPENAI_API_KEY is missing")
