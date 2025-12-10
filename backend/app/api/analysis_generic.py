from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.analysis import GenericAnalysisRequest, GenericAnalysisResult
from app.services.analysis_service import GenericAnalysisError, run_generic_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/run", response_model=GenericAnalysisResult)
async def run_analysis(req: GenericAnalysisRequest) -> GenericAnalysisResult:
    try:
        logger.info("generic_analysis.request", extra={"mission_id": req.mission_id})
        result = await run_generic_analysis(req)
        logger.info(
            "generic_analysis.success",
            extra={"mission_id": req.mission_id, "document_count": len(req.document_ids)},
        )
        return result
    except GenericAnalysisError as exc:
        logger.warning(
            "generic_analysis.error",
            extra={"mission_id": req.mission_id, "error": str(exc)},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "generic_analysis.unexpected_failure",
            extra={"mission_id": req.mission_id},
        )
        raise HTTPException(status_code=500, detail="Analysis failed") from exc
