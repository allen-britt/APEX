from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.authorities import AuthorityType
from app.schemas.humint import (
    HumintFollowup,
    HumintGap,
    HumintIirAnalysisResult,
    HumintIirParsedFields,
    HumintInsight,
)
from app.schemas.analysis import (
    FollowUpQuestion,
    GenericAnalysisRequest,
    GenericAnalysisResult,
)


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MissionBase(ORMBase):
    name: str
    description: Optional[str] = None
    primary_authority: str = AuthorityType.LEO.value
    original_authority: str = AuthorityType.LEO.value
    secondary_authorities: List[str] = Field(default_factory=list)
    int_types: List[str] = Field(default_factory=list)


class MissionCreate(MissionBase):
    pass


class MissionResponse(MissionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    kg_namespace: Optional[str] = None
    gap_analysis: Optional[Dict[str, Any]] = None
    template_reports: List[TemplateReportRecord] = Field(default_factory=list)
    authority_pivots: List["MissionAuthorityPivotResponse"] = Field(default_factory=list)
    latest_agent_run: Optional["AgentRunResponse"] = None


class MissionAuthorityPivotResponse(ORMBase):
    id: int
    from_authority: str
    to_authority: str
    justification: str
    risk: str
    conditions: List[str] = Field(default_factory=list)
    actor: Optional[str] = None
    created_at: datetime


class MissionAuthorityPivotRequest(BaseModel):
    target_authority: str
    justification: str


class DocumentBase(ORMBase):
    title: Optional[str] = None
    content: str
    include_in_analysis: bool = True


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(ORMBase):
    mission_id: Optional[int] = None
    include_in_analysis: Optional[bool] = None


class DocumentResponse(DocumentBase):
    id: int
    mission_id: int
    created_at: datetime


class MissionDocumentResponse(ORMBase):
    id: str
    mission_id: int
    source_type: str
    title: Optional[str] = None
    original_path: Optional[str] = None
    primary_int: Optional[str] = None
    int_types: List[str] = Field(default_factory=list)
    aggregator_doc_id: Optional[str] = None
    status: str
    created_at: datetime
    ingest_status: Optional[str] = None
    ingest_error: Optional[str] = None
    kg_nodes_before: Optional[int] = None
    kg_nodes_after: Optional[int] = None
    kg_edges_before: Optional[int] = None
    kg_edges_after: Optional[int] = None
    kg_nodes_delta: Optional[int] = None
    kg_edges_delta: Optional[int] = None


class MissionDocumentUrlRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    primary_int: Optional[str] = None
    int_types: List[str] = Field(default_factory=list)


class MissionIngestJobResponse(ORMBase):
    id: int
    mission_id: int
    document_id: str
    status: str
    attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MissionIngestJobDrainResponse(BaseModel):
    mission_id: int
    scheduled: bool = True


class EntityBase(ORMBase):
    name: str
    type: Optional[str] = None
    description: Optional[str] = None


class EntityCreate(EntityBase):
    pass


class EntityResponse(EntityBase):
    id: int
    mission_id: int
    created_at: datetime


class EventBase(ORMBase):
    title: str
    summary: Optional[str] = None
    timestamp: Optional[datetime] = None
    location: Optional[str] = None
    involved_entity_ids: List[str] = Field(default_factory=list)


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: int
    mission_id: int
    created_at: datetime

    @field_validator("involved_entity_ids", mode="before")
    @classmethod
    def _coerce_involved_entity_ids(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            try:
                parsed = json.loads(raw)
            except Exception:
                return [part.strip() for part in raw.split(",") if part.strip()]
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        return [str(value)]


class GapFinding(BaseModel):
    title: str
    detail: Optional[str] = None
    severity: str = "medium"
    metadata: Optional[Dict[str, Any]] = None


class PriorityEntry(BaseModel):
    name: str
    reason: str
    type: Optional[str] = None
    score: Optional[float] = None
    reference_id: Optional[int] = None


class PrioritiesBlock(BaseModel):
    entities: List[PriorityEntry] = Field(default_factory=list)
    events: List[PriorityEntry] = Field(default_factory=list)
    rationale: str = ""


class GapAnalysisResponse(BaseModel):
    generated_at: datetime
    kg_summary: Optional[Dict[str, Any]] = None
    missing_data: List[GapFinding] = Field(default_factory=list)
    time_gaps: List[GapFinding] = Field(default_factory=list)
    conflicts: List[GapFinding] = Field(default_factory=list)
    high_value_unknowns: List[GapFinding] = Field(default_factory=list)
    quality_findings: List[GapFinding] = Field(default_factory=list)
    priorities: PrioritiesBlock


class GapItem(BaseModel):
    id: str
    description: str
    severity: str = "medium"
    int_types_impacted: List[str] = Field(default_factory=list)
    evidence_notes: Optional[str] = None


class RecommendedAction(BaseModel):
    id: str
    description: str
    authority_scope: str
    allowed_under_mission_authority: bool = True
    rationale: Optional[str] = None
    related_gap_ids: List[str] = Field(default_factory=list)


class GapAnalysisResult(BaseModel):
    mission_id: int
    mission_authority: str
    coverage_summary: Dict[str, Any] = Field(default_factory=dict)
    gaps: List[GapItem] = Field(default_factory=list)
    recommended_actions: List[RecommendedAction] = Field(default_factory=list)
    overall_assessment: Optional[str] = None


class ReportTemplateBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    int_type: Optional[str] = None
    mission_domains: List[str] = Field(default_factory=list)
    title10_allowed: bool = False
    title50_allowed: bool = False
    allowed_authorities: List[str] = Field(default_factory=list)
    allowed_int_types: List[str] = Field(default_factory=list)
    int_types: List[str] = Field(default_factory=list)


class ReportTemplateSummary(ReportTemplateBase):
    sections: List[str] = Field(default_factory=list)


class ReportTemplateSection(BaseModel):
    id: str
    title: str
    content: str


class ReportTemplateResponse(BaseModel):
    template_id: str
    template_name: str
    sections: List[ReportTemplateSection]
    metadata: Dict[str, Any]


class TemplateReportRecord(BaseModel):
    id: str
    template_id: str
    template_name: str
    sections: List[ReportTemplateSection]
    metadata: Dict[str, Any]
    stored_at: datetime


class AuthorityInfo(BaseModel):
    code: str
    label: str
    description: str
    prompt_context: str
    prohibitions: str
    allowed_int_types: List[str] = Field(default_factory=list)
    ok_examples: List[str] = Field(default_factory=list)
    not_ok_examples: List[str] = Field(default_factory=list)


class TemplateReportGenerateRequest(BaseModel):
    template_id: str = Field(..., min_length=1)


class TemplateReportGenerateResponse(BaseModel):
    mission_id: int
    template_id: str
    template_name: str
    html: str
    markdown: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MissionDatasetBase(BaseModel):
    name: str
    status: str = "ready"
    sources: Any
    profile: Optional[Any] = None
    semantic_profile: Optional[Any] = None


class MissionDatasetCreate(MissionDatasetBase):
    """Payload when creating a dataset via POST /missions/{id}/datasets."""
    pass


class MissionDatasetRead(MissionDatasetBase):
    id: int
    mission_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class AgentRunResponse(ORMBase):
    id: int
    mission_id: int
    status: str
    summary: Optional[str] = None
    next_steps: Optional[str] = None
    guardrail_status: str
    guardrail_issues: List[Any] = Field(default_factory=list)
    raw_facts: Dict[str, Any] | List[Any] | None = None
    gaps: Dict[str, Any] | List[Any] | None = None
    delta_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class GuardrailReport(BaseModel):
    overall_score: str
    issues: List[str] = Field(default_factory=list)


class MissionReportResponse(BaseModel):
    mission: MissionResponse
    documents: List[DocumentResponse]
    run: Optional[AgentRunResponse] = None
    entities: List[EntityResponse]
    events: List[EventResponse]
    guardrail: Optional[GuardrailReport] = None
    gaps: Optional[List[str]] = None
    next_steps: Optional[List[str]] = None
    delta_summary: Optional[str] = None
    generated_at: datetime


class ApexMissionPayload(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    theater: Optional[str] = None
    created_at: str
    updated_at: str
    tags: List[str] = Field(default_factory=list)
    commander_intent: Optional[str] = None


class ApexDocumentPayload(BaseModel):
    id: int
    title: str
    source_type: Optional[str] = None
    origin: Optional[str] = None
    created_at: str
    ingested_at: Optional[str] = None
    include_in_analysis: bool
    classification: Optional[str] = None


class ApexEntityPayload(BaseModel):
    id: int
    name: str
    type: str
    role: Optional[str] = None
    confidence: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


class ApexEventPayload(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    timestamp: Optional[str] = None
    location: Optional[str] = None
    actors: List[int] = Field(default_factory=list)
    confidence: Optional[float] = None
    phase: Optional[str] = None


class ApexAgentRunPayload(BaseModel):
    id: Optional[int] = None
    status: str
    created_at: str
    profile: Optional[str] = None
    summary: Optional[str] = None
    next_steps: Optional[str] = None
    operational_estimate: Optional[str] = None
    raw_facts: Optional[str] = None
    gaps: Optional[str] = None
    delta_summary: Optional[str] = None


class ApexCrossDocumentInsights(BaseModel):
    key_drivers: List[str] = Field(default_factory=list)
    critical_vulnerabilities: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class ApexGuardrailStatus(BaseModel):
    heuristic_score: Optional[str] = None
    analytic_score: Optional[str] = None
    issues: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ApexReportMeta(BaseModel):
    generated_at: str
    generator_version: str
    model_name: Optional[str] = None
    template: Optional[str] = None


class ApexDeltaEntityChange(BaseModel):
    id: Optional[int] = None
    name: str
    previous_summary: Optional[str] = None
    current_summary: Optional[str] = None


class ApexDeltaEventChange(BaseModel):
    id: Optional[int] = None
    title: str
    previous_assessment: Optional[str] = None
    current_assessment: Optional[str] = None
    timestamp: Optional[str] = None


class ApexDeltaSection(BaseModel):
    previous_run_id: Optional[int] = None
    previous_run_timestamp: Optional[str] = None
    new_entities: List[ApexEntityPayload] = Field(default_factory=list)
    changed_entities: List[ApexDeltaEntityChange] = Field(default_factory=list)
    new_events: List[ApexEventPayload] = Field(default_factory=list)
    changed_events: List[ApexDeltaEventChange] = Field(default_factory=list)
    risk_delta_summary: Optional[str] = None
    updated_recommendations: List[str] = Field(default_factory=list)
    guardrail_new_issues: List[str] = Field(default_factory=list)
    new_document_count: int = 0


class ApexReportDataset(BaseModel):
    mission: ApexMissionPayload
    documents: List[ApexDocumentPayload]
    entities: List[ApexEntityPayload]
    events: List[ApexEventPayload]
    agent_run: ApexAgentRunPayload
    cross_doc_insights: ApexCrossDocumentInsights = Field(default_factory=ApexCrossDocumentInsights)
    guardrails: Optional[ApexGuardrailStatus] = None
    meta: ApexReportMeta
    delta: Optional[ApexDeltaSection] = None


MissionResponse.model_rebuild()
