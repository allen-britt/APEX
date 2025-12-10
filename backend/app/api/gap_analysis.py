from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db
from app.services.gap_analysis_service import GapAnalysisError, GapAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/missions/{mission_id}/gap_analysis", tags=["gap_analysis"])


def _get_mission_or_404(mission_id: int, db: Session) -> models.Mission:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission


@router.post("", response_model=schemas.GapAnalysisResult)
async def run_gap_analysis(
    mission_id: int,
    db: Session = Depends(get_db),
) -> schemas.GapAnalysisResult:
    _get_mission_or_404(mission_id, db)
    service = GapAnalysisService(db)
    try:
        logger.info("gap_analysis.request", extra={"mission_id": mission_id})
        result = await service.run_gap_analysis(mission_id)
        logger.info(
            "gap_analysis.success",
            extra={"mission_id": mission_id, "gap_count": len(result.gaps)},
        )
        return result
    except GapAnalysisError as exc:
        logger.exception(
            "gap_analysis.failure",
            extra={"mission_id": mission_id},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
