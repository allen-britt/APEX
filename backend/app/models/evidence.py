from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceIncident(BaseModel):
    id: str
    summary: str
    location: Optional[str] = None
    occurred_at: Optional[str] = None
    source_ids: List[str] = Field(default_factory=list)


class EvidenceSubject(BaseModel):
    id: str
    name: str
    type: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None


class EvidenceLocation(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    geo: Optional[str] = None


class EvidenceEvent(BaseModel):
    id: str
    type: Optional[str] = None
    description: Optional[str] = None
    occurred_at: Optional[str] = None
    location_id: Optional[str] = None


class EvidenceDocument(BaseModel):
    id: str
    title: str
    doc_type: Optional[str] = None
    source: Optional[str] = None


class EvidenceGap(BaseModel):
    id: str
    description: str
    severity: Optional[str] = None


class EvidenceBundle(BaseModel):
    mission_id: str
    mission_name: Optional[str] = None
    authority: Optional[str] = None
    int_lanes: List[str] = Field(default_factory=list)

    incidents: List[EvidenceIncident] = Field(default_factory=list)
    subjects: List[EvidenceSubject] = Field(default_factory=list)
    associates: List[EvidenceSubject] = Field(default_factory=list)
    locations: List[EvidenceLocation] = Field(default_factory=list)
    events: List[EvidenceEvent] = Field(default_factory=list)
    documents: List[EvidenceDocument] = Field(default_factory=list)
    gaps: List[EvidenceGap] = Field(default_factory=list)

    kg_snapshot_summary: Optional[str] = None
