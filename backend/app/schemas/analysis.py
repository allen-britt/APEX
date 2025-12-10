from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class GenericAnalysisRequest(BaseModel):
    mission_id: int
    document_ids: List[int] = Field(default_factory=list)
    profile: Literal["humint", "generic"] = "humint"


class FollowUpQuestion(BaseModel):
    target: str
    question: str


class GenericAnalysisResult(BaseModel):
    mission_id: int
    document_ids: List[int]
    profile: str

    summary: str
    key_entities: List[str] = Field(default_factory=list)
    key_events: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    follow_up_questions: List[FollowUpQuestion] = Field(default_factory=list)
    decision_note: str
