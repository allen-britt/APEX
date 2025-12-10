from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app import models, schemas
from app.services.coverage_service import CoverageService
from app.services.llm_client import LLMCallException, LLMRole, call_llm_with_role
from app.services.mission_context_service import MissionContextService
from app.services.kg_snapshot_utils import summarize_kg_snapshot
from app.services.policy_context import build_policy_prompt
from app.services.prompt_builder import build_global_system_prompt

logger = logging.getLogger(__name__)


GAP_ANALYSIS_TASK_INSTRUCTIONS = (
    "You are an intelligence analyst assistant performing policy-aware gap analysis for this mission."
    "\n- Fuse the mission context, structured intel, coverage map, and knowledge graph metrics to find gaps."
    "\n- Highlight weak or missing INT coverage and cite observed evidence or contradictions."
    "\n- Recommend only those follow-up actions that are legal for the current authority and INT mix."
    "\n- Always reason with the supplied guardrails before answering."
)


def _build_gap_analysis_system_prompt(mission_context: Dict[str, Any]) -> str:
    return build_global_system_prompt(mission_context, GAP_ANALYSIS_TASK_INSTRUCTIONS)


class GapAnalysisError(Exception):
    """Raised when a gap analysis cannot be completed."""


class GapAnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._context_service = MissionContextService(db)
        self._coverage_service = CoverageService()

    async def run_gap_analysis(self, mission_id: int) -> schemas.GapAnalysisResult:
        mission = self._get_mission_or_raise(mission_id)
        context = self._context_service.build_context(mission_id)
        coverage_summary = self._coverage_service.build_coverage_map(context)

        try:
            llm_payload = await self._invoke_llm(
                context=context,
                coverage=coverage_summary,
            )
        except GapAnalysisError as exc:
            logger.warning("Gap analysis LLM flow failed: %s", exc)
            return self._fallback_result(mission, coverage_summary, str(exc))

        payload = self._compose_payload(mission, coverage_summary, llm_payload)
        return schemas.GapAnalysisResult(**payload)

    async def _invoke_llm(
        self,
        *,
        context: Dict[str, Any],
        coverage: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt_context: Dict[str, Any] = dict(context)
        mission_block = prompt_context.get("mission")
        if isinstance(mission_block, dict):
            prompt_context.setdefault("authority", mission_block.get("mission_authority"))
            prompt_context.setdefault("int_types", mission_block.get("int_types"))
        prompt_context["coverage_summary"] = coverage

        system_prompt = _build_gap_analysis_system_prompt(prompt_context)
        context_json = json.dumps(context, ensure_ascii=False, indent=2)
        coverage_json = json.dumps(coverage, ensure_ascii=False, indent=2)
        kg_summary = summarize_kg_snapshot(context.get("kg_snapshot"))
        mission_name = (mission_block or {}).get("name") if isinstance(mission_block, dict) else None
        user_prompt = (
            (f"Mission: {mission_name}\n" if mission_name else "")
            + "Mission context JSON:\n"
            f"{context_json}\n\n"
            "Coverage map JSON:\n"
            f"{coverage_json}\n\n"
            "Knowledge graph summary:\n"
            f"{kg_summary}\n\n"
            "Output JSON with keys: gaps (array), recommended_actions (array), overall_assessment (string)."
            " Each gap should include id, description, severity, int_types_impacted, evidence_notes."
            " Each recommended action should include id, description, authority_scope,"
            " allowed_under_mission_authority, rationale, related_gap_ids."
        )

        policy_block = self._build_policy_block(prompt_context)

        try:
            raw = await call_llm_with_role(
                prompt=user_prompt,
                system=system_prompt,
                policy_block=policy_block,
                role=LLMRole.ANALYSIS_PRIMARY,
            )
        except LLMCallException as exc:
            raise GapAnalysisError("LLM call failed") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GapAnalysisError("LLM returned non-JSON response") from exc

        if not isinstance(data, dict):
            raise GapAnalysisError("LLM response must be a JSON object")
        return data

    def _build_policy_block(self, prompt_context: Dict[str, Any]) -> str | None:
        mission_block = prompt_context.get("mission") or {}
        authority = mission_block.get("mission_authority") or prompt_context.get("authority")
        int_types = (
            prompt_context.get("int_types")
            or mission_block.get("int_types")
            or []
        )
        history_lines = mission_block.get("authority_history_lines")
        if not authority and not int_types:
            return None
        return build_policy_prompt(authority, int_types, authority_history=history_lines)

    def _compose_payload(
        self,
        mission: models.Mission,
        coverage_summary: Dict[str, Any],
        llm_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        gaps = self._normalize_gaps(llm_payload.get("gaps"))
        actions = self._normalize_actions(llm_payload.get("recommended_actions"))
        overall = llm_payload.get("overall_assessment")

        return {
            "mission_id": mission.id,
            "mission_authority": mission.mission_authority,
            "coverage_summary": coverage_summary,
            "gaps": gaps,
            "recommended_actions": actions,
            "overall_assessment": overall,
        }

    def _normalize_gaps(self, raw_gaps: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_gaps, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for idx, gap in enumerate(raw_gaps, start=1):
            if not isinstance(gap, dict):
                continue
            gap_id = str(gap.get("id") or f"gap_{idx}")
            description = str(gap.get("description") or gap.get("summary") or "Unspecified gap")
            severity = str(gap.get("severity") or "medium")
            ints = gap.get("int_types_impacted") or []
            evidence = gap.get("evidence_notes")
            normalized.append(
                {
                    "id": gap_id,
                    "description": description,
                    "severity": severity,
                    "int_types_impacted": [str(entry) for entry in ints if entry],
                    "evidence_notes": str(evidence) if evidence else None,
                }
            )
        return normalized

    def _normalize_actions(self, raw_actions: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_actions, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for idx, action in enumerate(raw_actions, start=1):
            if not isinstance(action, dict):
                continue
            action_id = str(action.get("id") or f"action_{idx}")
            description = str(action.get("description") or "Unspecified action")
            scope = str(action.get("authority_scope") or "LEO")
            allowed = bool(action.get("allowed_under_mission_authority", True))
            rationale = action.get("rationale")
            related = action.get("related_gap_ids") or []
            normalized.append(
                {
                    "id": action_id,
                    "description": description,
                    "authority_scope": scope,
                    "allowed_under_mission_authority": allowed,
                    "rationale": str(rationale) if rationale else None,
                    "related_gap_ids": [str(entry) for entry in related if entry],
                }
            )
        return normalized

    def _fallback_result(
        self,
        mission: models.Mission,
        coverage_summary: Dict[str, Any],
        message: str,
    ) -> schemas.GapAnalysisResult:
        return schemas.GapAnalysisResult(
            mission_id=mission.id,
            mission_authority=mission.mission_authority,
            coverage_summary=coverage_summary,
            gaps=[],
            recommended_actions=[],
            overall_assessment=message,
        )

    def _get_mission_or_raise(self, mission_id: int) -> models.Mission:
        mission = self.db.query(models.Mission).filter(models.Mission.id == mission_id).first()
        if not mission:
            raise GapAnalysisError("Mission not found")
        return mission
