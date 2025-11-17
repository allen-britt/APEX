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
