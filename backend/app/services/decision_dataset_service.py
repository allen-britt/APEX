from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import models
from app.models.decision_dataset import DecisionDataset
from app.services.llm_client import LLMClient, LlmError
from app.services.mission_context_service import MissionContextError, MissionContextService
from app.services.kg_snapshot_utils import summarize_kg_snapshot

logger = logging.getLogger(__name__)

_JSON_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json_payload(raw_text: str) -> Optional[str]:
    if not raw_text:
        return None
    stripped = raw_text.strip()
    if not stripped:
        return None
    if stripped.startswith("{"):
        return stripped
    match = _JSON_CODE_FENCE_RE.search(raw_text)
    if match:
        return match.group(1).strip()
    first = raw_text.find("{")
    last = raw_text.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = raw_text[first : last + 1]
        return candidate.strip()
    return None

DECISION_JSON_SCHEMA_SNIPPET = """
You MUST respond with a single JSON object matching this TypeScript schema:

export interface CourseOfAction {
  id: string;
  decision_id: string;
  label: string;
  summary: string;
  pros: string[];
  cons: string[];
  risk_level: "low" | "medium" | "high" | "critical";
  policy_alignment: "compliant" | "waiver_required" | "conflicts";
  policy_refs: string[];
  confidence: number | null;
}

export interface PolicyCheck {
  id: string;
  rule_name: string;
  outcome: "pass" | "fail" | "waiver";
  summary: string;
  source_ref: string;
}

export interface DecisionPrecedent {
  id: string;
  mission_id: string;
  mission_name: string;
  run_id?: string;
  summary: string;
  outcome_summary?: string;
}

export interface DecisionBlindSpot {
  id: string;
  description: string;
  impact: "low" | "medium" | "high";
  mitigation?: string;
}

export interface MissionDecision {
  id: string;
  question: string;
  status: "pending" | "decided" | "deferred";
  recommended_coa_id?: string;
  selected_coa_id?: string;
  rationale?: string;
}

export interface DecisionDataset {
  decisions: MissionDecision[];
  courses_of_action: CourseOfAction[];
  policy_checks: PolicyCheck[];
  precedents: DecisionPrecedent[];
  blind_spots: DecisionBlindSpot[];
  system_confidence?: number;
}

Every CourseOfAction MUST include decision_id that references the id of the MissionDecision it belongs to.

Example payload:

{
  "decisions": [
    {
      "id": "decision-alpha",
      "question": "Do we reinforce the northern approach?",
      "status": "pending"
    }
  ],
  "courses_of_action": [
    {
      "id": "coa-alpha-1",
      "decision_id": "decision-alpha",
      "label": "Deploy reserve platoon",
      "summary": "Shift reserve platoon to cover the gap",
      "pros": ["Rapid response"],
      "cons": ["Reduces central reserve"],
      "risk_level": "medium",
      "policy_alignment": "compliant",
      "policy_refs": ["ROE-12"],
      "confidence": 0.82
    }
  ],
  "policy_checks": [],
  "precedents": [],
  "blind_spots": []
}
"""

DECISION_SYSTEM_PROMPT = (
    "You are an experienced operations analyst. Given mission context, structured intel, and policy constraints, "
    "you will identify concrete decision points with viable courses of action.\n\n"
    "Your job is NOT to narrate a report. Your job is to:\n"
    "- Propose up to {max_decisions} explicit decisions the commander must make.\n"
    "- For each decision, propose up to {max_coas} concrete Courses of Action (COAs).\n"
    "- Evaluate each COA for risk, policy alignment, and pros/cons.\n"
    "- Surface policy checks, precedents, and blind spots that affect decision-making.\n\n"
    "Return ONLY a JSON object that matches the provided schema."
)


def _serialize_run(run: models.AgentRun | None) -> Dict[str, Any] | None:
    if not run:
        return None
    return {
        "id": run.id,
        "status": run.status,
        "summary": run.summary,
        "next_steps": run.next_steps,
        "guardrail_status": run.guardrail_status,
        "guardrail_issues": list(run.guardrail_issues or []),
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }


class DecisionDatasetService:
    def __init__(
        self,
        db: Session,
        *,
        context_service: MissionContextService | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.db = db
        self._context_service = context_service or MissionContextService(db)
        self._llm = llm_client or LLMClient()

    def build_decision_dataset(
        self,
        *,
        mission: models.Mission,
        run_id: Optional[int] = None,
        context: Dict[str, Any] | None = None,
        max_decisions: int = 3,
        max_coas_per_decision: int = 3,
    ) -> DecisionDataset | None:
        try:
            mission_context = context or self._context_service.build_context_for_mission(mission)
        except MissionContextError:
            logger.exception("Failed to build mission context for mission_id=%s", mission.id)
            return None

        run_payload = mission_context.get("latest_agent_run")
        run_obj: models.AgentRun | None = None
        if run_id:
            run_obj = (
                self.db.query(models.AgentRun)
                .filter(models.AgentRun.id == run_id, models.AgentRun.mission_id == mission.id)
                .first()
            )
            if run_obj:
                run_payload = _serialize_run(run_obj)
        elif run_payload:
            # ensure we have the full payload from DB if not already
            run_obj = (
                self.db.query(models.AgentRun)
                .filter(models.AgentRun.id == run_payload.get("id"), models.AgentRun.mission_id == mission.id)
                .first()
            )
            if run_obj:
                run_payload = _serialize_run(run_obj)

        if not run_payload:
            logger.info("No agent run available for mission %s; skipping decision dataset", mission.id)
            return None

        kg_snapshot = mission_context.get("kg_snapshot")
        kg_summary = (
            mission_context.get("kg_snapshot_summary")
            or mission_context.get("kg_summary")
            or summarize_kg_snapshot(kg_snapshot)
        )

        prompt_context = {
            "mission": mission_context.get("mission"),
            "documents": mission_context.get("documents"),
            "entities": mission_context.get("entities"),
            "events": mission_context.get("events"),
            "datasets": mission_context.get("datasets"),
            "gap_analysis": mission_context.get("gap_analysis"),
            "kg_snapshot": kg_snapshot,
            "kg_snapshot_summary": kg_summary,
            "agent_run": run_payload,
        }

        policy_context_lines = [
            f"Mission authority: {mission.mission_authority}",
            f"INT types: {', '.join(mission.int_types or []) or 'unspecified'}",
        ]
        guardrail_status = run_payload.get("guardrail_status") if isinstance(run_payload, dict) else None
        if guardrail_status:
            policy_context_lines.append(f"Guardrail posture: {guardrail_status}")
        policy_context_text = "\n".join(policy_context_lines)

        user_prompt = (
            f"MISSION CONTEXT\n===============\n"
            f"Mission ID: {mission.id}\n"
            f"Run ID: {run_payload.get('id')}\n\n"
            f"Structured context JSON follows:\n{json.dumps(prompt_context, ensure_ascii=False, indent=2)}\n\n"
            f"POLICY CONTEXT\n===============\n{policy_context_text}\n\n"
            f"CONSTRAINTS\n===========\n"
            f"- Focus on up to {max_decisions} high-impact decisions.\n"
            f"- Provide realistic COAs grounded in the mission authority and guardrails.\n"
            f"- Use policy_refs for specific ROE/SOP identifiers when possible.\n"
            f"- Surface missing information as DecisionBlindSpot entries.\n\n"
            f"OUTPUT REQUIREMENTS\n===================\n{DECISION_JSON_SCHEMA_SNIPPET}"
        )

        system_prompt = DECISION_SYSTEM_PROMPT.format(
            max_decisions=max_decisions,
            max_coas=max_coas_per_decision,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            raw_response = self._llm.chat(messages)
        except LlmError:
            logger.exception("Decision dataset LLM call failed for mission_id=%s", mission.id)
            return None

        payload_text = _extract_json_payload(raw_response)
        if not payload_text:
            logger.warning("Decision dataset response did not contain JSON payload: %s", raw_response)
            return None

        try:
            data = json.loads(payload_text)
        except json.JSONDecodeError:
            logger.warning("Decision dataset response was not valid JSON after extraction: %s", payload_text)
            return None

        coas = data.get("courses_of_action")
        if isinstance(coas, list):
            missing_decision_links = [coa for coa in coas if not isinstance(coa, dict) or not coa.get("decision_id")]
            if missing_decision_links:
                logger.warning(
                    "Rejecting decision dataset: %s COAs missing decision_id",
                    len(missing_decision_links),
                )
                return None

        try:
            return DecisionDataset.model_validate(data)
        except ValidationError:
            logger.exception("Decision dataset response failed validation")
            return None

