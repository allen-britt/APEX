"""Pydantic schemas for HUMINT IIR analysis outputs (UNCLASSIFIED)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class HumintIirParsedFields(BaseModel):
    """Best-effort structured fields parsed from a HUMINT IIR."""

    report_number: Optional[str] = None
    source_id: Optional[str] = None
    collection_unit: Optional[str] = None
    collection_date: Optional[str] = None
    report_date: Optional[str] = None
    region: Optional[str] = None
    target_persons: List[str] = Field(default_factory=list)
    target_locations: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    handling_instructions: Optional[str] = None


class HumintInsight(BaseModel):
    """Actionable insight extracted from HUMINT reporting."""

    id: Optional[int] = None
    title: str
    detail: str
    confidence: float
    supporting_evidence_ids: List[int] = Field(default_factory=list)


class HumintGap(BaseModel):
    """Collection gap derived from HUMINT analysis."""

    title: str
    description: str
    priority: int
    suggested_collection: Optional[str] = None


class HumintFollowup(BaseModel):
    """Recommended follow-up questions or coordination steps."""

    question: str
    rationale: str
    priority: int
    related_gap_titles: List[str] = Field(default_factory=list)
    suggested_channel: Optional[str] = None


class HumintIirAnalysisResult(BaseModel):
    """Structured HUMINT IIR analysis suitable for DIA workflows (UNCLASSIFIED)."""

    mission_id: int
    document_id: int
    parsed_fields: HumintIirParsedFields
    key_insights: List[HumintInsight]
    contradictions: List[str] = Field(default_factory=list)
    gaps: List[HumintGap]
    followups: List[HumintFollowup]
    evidence_document_ids: List[int] = Field(default_factory=list)
    model_name: Optional[str] = None
    run_id: Optional[int] = None
