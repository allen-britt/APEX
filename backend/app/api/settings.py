from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config_llm import get_active_llm_name, set_active_llm_name


router = APIRouter(prefix="", tags=["settings"])


@router.get("/settings/model")
def get_active_model() -> dict[str, str]:
    return {"active_model": get_active_llm_name()}


class ModelSelection(BaseModel):
    model: str


@router.post("/settings/model", status_code=status.HTTP_200_OK)
def set_model(selection: ModelSelection) -> dict[str, str]:
    candidate = selection.model.strip()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Model name is required")

    try:
        set_active_llm_name(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"active_model": candidate}
