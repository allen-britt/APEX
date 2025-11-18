from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MissionBase(ORMBase):
    name: str
    description: Optional[str] = None


class MissionCreate(MissionBase):
    pass


class MissionResponse(MissionBase):
    id: int
    created_at: datetime
    updated_at: datetime


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
    involved_entity_ids: List[Union[int, str]] = Field(default_factory=list)


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: int
    mission_id: int
    created_at: datetime


class AgentRunResponse(ORMBase):
    id: int
    mission_id: int
    status: str
    summary: Optional[str] = None
    next_steps: Optional[str] = None
    guardrail_status: str
    guardrail_issues: List[str] = Field(default_factory=list)
    raw_facts: Optional[List[dict]] = None
    gaps: Optional[List[dict]] = None
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
