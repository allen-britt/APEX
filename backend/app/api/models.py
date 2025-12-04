from __future__ import annotations

from fastapi import APIRouter

from app.config_llm import get_active_llm_name
from app.services.llm_client import LLMClient

router = APIRouter(prefix="/models", tags=["models"])
_client = LLMClient()


@router.get("/available")
def get_available_models() -> dict:
    """Return known local LLMs for the frontend settings UI."""
    return {"models": _client.list_models()}


@router.get("/active")
def get_active_model() -> dict:
    """Expose the current active LLM selection."""
    return {"active_model": get_active_llm_name()}
