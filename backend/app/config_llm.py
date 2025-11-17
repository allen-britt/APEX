from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


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


def get_llm_config() -> LLMConfig:
    global _cached_config
    if _cached_config is None:
        base_url = os.getenv("APEX_LLM_BASE_URL", "http://localhost:11434/v1/chat")
        api_key = os.getenv("APEX_LLM_API_KEY") or None
        model = os.getenv("APEX_LLM_MODEL", "local-llm")
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
