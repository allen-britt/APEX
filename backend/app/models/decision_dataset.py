from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel


RiskLevel = Literal["low", "medium", "high", "critical"]
PolicyAlignment = Literal["compliant", "waiver_required", "conflicts"]
PolicyOutcome = Literal["pass", "fail", "waiver"]
BlindSpotImpact = Literal["low", "medium", "high"]
DecisionStatus = Literal["pending", "decided", "deferred"]


class CourseOfAction(BaseModel):
    id: str
    decision_id: str
    label: str
    summary: str
    pros: List[str]
    cons: List[str]
    risk_level: RiskLevel
    policy_alignment: PolicyAlignment
    policy_refs: List[str]
    confidence: Optional[float] = None


class PolicyCheck(BaseModel):
    id: str
    rule_name: str
    outcome: PolicyOutcome
    summary: str
    source_ref: str


class DecisionPrecedent(BaseModel):
    id: str
    mission_id: str
    mission_name: str
    run_id: Optional[str] = None
    summary: str
    outcome_summary: Optional[str] = None


class DecisionBlindSpot(BaseModel):
    id: str
    description: str
    impact: BlindSpotImpact
    mitigation: Optional[str] = None


class MissionDecision(BaseModel):
    id: str
    question: str
    status: DecisionStatus
    recommended_coa_id: Optional[str] = None
    selected_coa_id: Optional[str] = None
    rationale: Optional[str] = None


class DecisionDataset(BaseModel):
    decisions: List[MissionDecision]
    courses_of_action: List[CourseOfAction]
    policy_checks: List[PolicyCheck]
    precedents: List[DecisionPrecedent]
    blind_spots: List[DecisionBlindSpot]
    system_confidence: Optional[float] = None
