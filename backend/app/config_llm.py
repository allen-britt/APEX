from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class LocalLlmModel:
    """Configuration for a locally hosted LLM instance."""

    name: str
    display_name: str
    base_url: str
    kind: str


_DEFAULT_MODELS: List[LocalLlmModel] = [
    LocalLlmModel(
        name="mistral",
        display_name="Local Mistral (Ollama)",
        base_url=os.getenv("LLM_MISTRAL_URL", "http://localhost:11434"),
        kind="ollama_chat",
    ),
    LocalLlmModel(
        name="phi3",
        display_name="Local Phi-3 (Ollama)",
        base_url=os.getenv("LLM_PHI3_URL", "http://localhost:11434"),
        kind="ollama_chat",
    ),
]


def get_available_llms() -> List[LocalLlmModel]:
    return _DEFAULT_MODELS


def get_llm_by_name(name: str) -> LocalLlmModel:
    for model in get_available_llms():
        if model.name == name:
            return model
    raise ValueError(f"Unknown LLM model: {name!r}")


_ENV_ACTIVE_KEY = "APEX_ACTIVE_LLM_MODEL"


def get_active_llm_name() -> str:
    active = os.getenv(_ENV_ACTIVE_KEY)
    if active:
        return active
    return get_available_llms()[0].name


def set_active_llm_name(name: str) -> None:
    get_llm_by_name(name)  # validate exists
    os.environ[_ENV_ACTIVE_KEY] = name
    _invalidate_cached_config()


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: Optional[str]
    model: str
    demo_mode: bool
    model_config_path: str


def _str_to_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


_cached_config: LLMConfig | None = None


def _invalidate_cached_config() -> None:
    global _cached_config
    _cached_config = None


def _resolve_base_url() -> str:
    override = os.getenv("APEX_LLM_BASE_URL")
    if override:
        return override.rstrip("/") or "http://localhost:11434"

    active_name = os.getenv("APEX_LLM_MODEL", get_active_llm_name())
    model_cfg = get_llm_by_name(active_name)
    return model_cfg.base_url.rstrip("/")


def get_llm_config() -> LLMConfig:
    global _cached_config
    if _cached_config is None:
        base_url = _resolve_base_url()
        api_key = os.getenv("APEX_LLM_API_KEY") or None
        model = os.getenv("APEX_LLM_MODEL", get_active_llm_name())
        demo_mode = _str_to_bool(os.getenv("APEX_LLM_DEMO_MODE"), default=False)
        model_config_path = os.getenv("APEX_LLM_MODEL_CONFIG_PATH", "model_config.json")

        _cached_config = LLMConfig(
            base_url=base_url,
            api_key=api_key,
            model=model,
            demo_mode=demo_mode,
            model_config_path=model_config_path,
        )
    return _cached_config


def is_demo_mode() -> bool:
    return get_llm_config().demo_mode
