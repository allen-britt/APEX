"""HUMINT analysis API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import HumintIirAnalysisResult
from app.services import extraction_service as extraction_module
from app.services.evidence_extractor_service import EvidenceExtractorService
from app.services.humint_iir_analysis_service import (
    ExtractionServiceProtocol,
    HumintIirAnalysisService,
)
from app.services.llm_client import LLMClient


router = APIRouter(prefix="/missions/{mission_id}/humint", tags=["humint"])


def get_llm_client() -> LLMClient:
    return LLMClient()


def get_extraction_service() -> ExtractionServiceProtocol:
    return extraction_module


def get_evidence_extractor(db: Session = Depends(get_db)) -> EvidenceExtractorService:
    return EvidenceExtractorService(session=db)


def get_humint_iir_analysis_service(
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
    extraction_service: ExtractionServiceProtocol = Depends(get_extraction_service),
    evidence_extractor: EvidenceExtractorService = Depends(get_evidence_extractor),
) -> HumintIirAnalysisService:
    return HumintIirAnalysisService(
        db=db,
        llm_client=llm_client,
        extraction_service=extraction_service,
        evidence_extractor=evidence_extractor,
    )


@router.post(
    "/documents/{document_id}/analyze",
    response_model=HumintIirAnalysisResult,
)
async def analyze_humint_iir(
    mission_id: int,
    document_id: int,
    humint_service: HumintIirAnalysisService = Depends(get_humint_iir_analysis_service),
) -> HumintIirAnalysisResult:
    """Analyze a HUMINT IIR and return UNCLASSIFIED structured output."""

    return await humint_service.analyze_iir(
        mission_id=mission_id,
        document_id=document_id,
    )
