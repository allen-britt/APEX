from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db
from app.services.legacy_gap_analysis_service import GapAnalysisError, LegacyGapAnalysisService

router = APIRouter(prefix="/missions/{mission_id}/analysis", tags=["analysis"])


def get_gap_service() -> LegacyGapAnalysisService:
    return LegacyGapAnalysisService()


def _get_mission_or_404(mission_id: int, db: Session) -> models.Mission:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission


def _normalize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(data)
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, str):
        try:
            payload["generated_at"] = datetime.fromisoformat(generated_at)
        except ValueError:
            payload["generated_at"] = datetime.now(timezone.utc)
    elif not isinstance(generated_at, datetime):
        payload["generated_at"] = datetime.now(timezone.utc)
    return payload


def _serialize_for_storage(result: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(result)
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, datetime):
        payload["generated_at"] = generated_at.isoformat()
    return payload


@router.get("/gaps", response_model=schemas.GapAnalysisResponse)
async def get_gap_analysis(
    mission_id: int,
    force_regen: bool = Query(False, alias="force_regen"),
    db: Session = Depends(get_db),
    service: LegacyGapAnalysisService = Depends(get_gap_service),
) -> schemas.GapAnalysisResponse:
    mission = _get_mission_or_404(mission_id, db)

    if not force_regen and mission.gap_analysis:
        if isinstance(mission.gap_analysis, dict):
            payload = _normalize_result(mission.gap_analysis)
            return schemas.GapAnalysisResponse(**payload)
        logger.warning("Mission %s gap_analysis persisted in unexpected format", mission_id)

    try:
        result = await service.analyze(mission_id, db)
    except GapAnalysisError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    mission.gap_analysis = _serialize_for_storage(result)
    db.add(mission)
    db.commit()
    db.refresh(mission)

    payload = _normalize_result(mission.gap_analysis)
    return schemas.GapAnalysisResponse(**payload)
