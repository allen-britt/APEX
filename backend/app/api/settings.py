from __future__ import annotations

import subprocess
from typing import Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services import llm_client


router = APIRouter(prefix="", tags=["settings"])


def _list_ollama_models() -> List[Dict[str, str]]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []

    models: List[Dict[str, str]] = []
    lines = result.stdout.strip().splitlines()
    for line in lines[1:]:  # skip header row
        name = line.split()[0].strip()
        if name:
            models.append({"name": name, "source": "ollama"})
    return models


def _fallback_models() -> List[Dict[str, str]]:
    active = llm_client.get_active_model()
    return [{"name": active, "source": "config"}]


@router.get("/models/available")
def list_models() -> Dict[str, List[Dict[str, str]]]:
    models = _list_ollama_models()
    if not models:
        models = _fallback_models()
    return {"models": models}


@router.get("/settings/model")
def get_active_model() -> Dict[str, str]:
    return {"active_model": llm_client.get_active_model()}


class ModelSelection(BaseModel):
    model: str


@router.post("/settings/model", status_code=status.HTTP_200_OK)
def set_model(selection: ModelSelection) -> Dict[str, str]:
    candidate = selection.model.strip()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Model name is required")

    llm_client.set_active_model(candidate)
    return {"active_model": candidate}
