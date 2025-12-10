from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Dict, Iterable, List

from sqlalchemy.orm import Session

from app import models
from app.db.session import SessionLocal
from app.schemas.analysis import GenericAnalysisRequest, GenericAnalysisResult
from app.services.llm_client import (
    LLMCallException,
    LLMRole,
    _normalize_and_parse_json,
    _repair_json_with_utility,
    call_llm_with_role,
)
from app.services.mission_context_service import MissionContextService, MissionContextError
from app.services.kg_snapshot_utils import summarize_kg_snapshot

logger = logging.getLogger(__name__)


class GenericAnalysisError(Exception):
    """Raised when the generic analysis flow cannot complete."""


@dataclass(slots=True)
class MissionSnapshot:
    id: int
    name: str
    description: str | None
    authority: str


@dataclass(slots=True)
class DocumentSnapshot:
    id: int
    title: str | None
    content: str


GENERIC_SYSTEM_PROMPT = """
You are an intelligence analysis assistant. You analyze sets of reports and
produce structured JSON for downstream systems.

You MUST:
- Read all provided context carefully.
- Reason step-by-step internally.
- Return ONLY valid JSON matching the requested schema.
- Never include explanations or commentary outside the JSON.
""".strip()

HUMINT_PROFILE_HINT = """
PROFILE: HUMINT

Treat these documents as HUMINT-style reporting (e.g., IIRs, debriefs, contact reports).
Use appropriate HUMINT analytic language where natural, but keep outputs concise and
focused on operator and decision-maker needs.
""".strip()

GENERIC_PROFILE_HINT = """
PROFILE: GENERIC

Treat these documents as generic analytical reports. Use neutral, non-domain-specific
language suited for a general intelligence analysis context.
""".strip()

STRICT_JSON_POLICY_BLOCK = """
POLICY: You must respond with a single JSON object that exactly matches the schema provided later.
Do NOT include prose, explanations, markdown, code fences, or any characters before the opening brace.
If a field has no content, emit an empty string "" or empty array [] as appropriate.
Invalid responses will be rejected and you will be asked to try again.
""".strip()

def _get_session() -> Session:
    return SessionLocal()


def _snapshot_mission(session: Session, mission_id: int) -> MissionSnapshot:
    mission = session.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise GenericAnalysisError("Mission not found")
    return MissionSnapshot(
        id=mission.id,
        name=mission.name,
        description=mission.description,
        authority=mission.mission_authority,
    )


def _snapshot_documents(
    session: Session,
    mission_id: int,
    document_ids: Iterable[int],
) -> List[DocumentSnapshot]:
    ids = list(dict.fromkeys(document_ids))
    if not ids:
        raise GenericAnalysisError("At least one document id is required")

    docs = (
        session.query(models.Document)
        .filter(models.Document.mission_id == mission_id, models.Document.id.in_(ids))
        .all()
    )
    found_ids = {doc.id for doc in docs}
    missing = [doc_id for doc_id in ids if doc_id not in found_ids]
    if missing:
        raise GenericAnalysisError(f"Documents not found or not part of mission: {missing}")

    snapshots: List[DocumentSnapshot] = []
    for doc in docs:
        snapshots.append(
            DocumentSnapshot(
                id=doc.id,
                title=doc.title,
                content=(doc.content or ""),
            )
        )
    return snapshots


def _safe_entity_highlights(raw_entities: Any, limit: int = 10) -> List[str]:
    highlights: List[str] = []
    if not isinstance(raw_entities, list):
        return highlights
    for entry in raw_entities:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or entry.get("title") or "").strip()
        if not name:
            continue
        label = (entry.get("type") or entry.get("role") or "").strip()
        highlight = f"{name} ({label})" if label else name
        highlights.append(highlight)
        if len(highlights) >= limit:
            break
    return highlights


def _safe_event_highlights(raw_events: Any, limit: int = 8) -> List[str]:
    highlights: List[str] = []
    if not isinstance(raw_events, list):
        return highlights
    for entry in raw_events:
        if not isinstance(entry, dict):
            continue
        title = (entry.get("title") or entry.get("name") or "").strip()
        if not title:
            continue
        location = (entry.get("location") or entry.get("place") or "").strip()
        timestamp = (entry.get("timestamp") or entry.get("time") or "").strip()
        parts = [title]
        if location:
            parts.append(f"@ {location}")
        if timestamp:
            parts.append(f"[{timestamp}]")
        highlights.append(" ".join(parts))
        if len(highlights) >= limit:
            break
    return highlights


def _serialize_latest_run(raw_run: Any) -> Dict[str, Any] | None:
    if not isinstance(raw_run, dict):
        return None
    return {
        "id": raw_run.get("id"),
        "status": raw_run.get("status"),
        "summary": raw_run.get("summary"),
        "next_steps": raw_run.get("next_steps"),
        "guardrail_status": raw_run.get("guardrail_status"),
        "created_at": raw_run.get("created_at"),
    }


def _build_analysis_context(
    session: Session,
    mission: MissionSnapshot,
    documents: List[DocumentSnapshot],
) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "mission": {
            "id": mission.id,
            "name": mission.name,
            "description": mission.description,
            "authority": mission.authority,
        },
        "documents": [
            {
                "id": doc.id,
                "title": doc.title or f"Document #{doc.id}",
                "content": doc.content,
            }
            for doc in documents
        ],
        "document_count": len(documents),
    }

    mission_context: Dict[str, Any] | None = None
    try:
        mission_context = MissionContextService(session).build_context(mission.id)
    except MissionContextError as exc:
        logger.warning(
            "generic_analysis.context_failed",
            extra={"mission_id": mission.id, "error": str(exc)},
        )

    if isinstance(mission_context, dict):
        mission_block = mission_context.get("mission")
        if isinstance(mission_block, dict):
            context["mission"].update({
                "int_types": mission_block.get("int_types"),
                "kg_namespace": mission_block.get("kg_namespace"),
                "authority_history": mission_block.get("authority_history"),
            })

        entities_highlights = _safe_entity_highlights(mission_context.get("entities"))
        if entities_highlights:
            context["entity_highlights"] = entities_highlights

        event_highlights = _safe_event_highlights(mission_context.get("events"))
        if event_highlights:
            context["event_highlights"] = event_highlights

        gap_analysis = mission_context.get("gap_analysis")
        if gap_analysis:
            context["gap_analysis"] = gap_analysis

        latest_run = _serialize_latest_run(mission_context.get("latest_agent_run"))
        if latest_run:
            context["latest_agent_run"] = latest_run

        kg_snapshot = mission_context.get("kg_snapshot")
        kg_summary = (
            mission_context.get("kg_summary")
            or mission_context.get("kg_snapshot_summary")
            or summarize_kg_snapshot(kg_snapshot)
        )
        if kg_summary:
            context["kg_snapshot_summary"] = kg_summary

    if "kg_snapshot_summary" not in context:
        context["kg_snapshot_summary"] = "No KG snapshot available."

    return context


def _normalize_strings(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _normalize_followups(value: Any) -> List[Dict[str, str]]:
    if value is None:
        return []
    normalized: List[Dict[str, str]] = []

    candidates = value if isinstance(value, list) else [value]
    for entry in candidates:
        if isinstance(entry, dict):
            question = str(entry.get("question") or "").strip()
            if not question:
                continue
            target = str(entry.get("target") or "General").strip() or "General"
            normalized.append({"target": target, "question": question})
        else:
            question = str(entry).strip()
            if question:
                normalized.append({"target": "General", "question": question})

    return normalized


def _parse_llm_response(raw: str) -> Dict[str, object]:
    try:
        data = _normalize_and_parse_json(raw)
    except JSONDecodeError as exc:
        preview = (raw or "")[:500]
        logger.warning("generic_analysis.json_parse_failed preview=%r error=%s", preview, exc)
        raise GenericAnalysisError("LLM returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise GenericAnalysisError("LLM response must be a JSON object")
    return data


async def _parse_or_repair_response(raw: str) -> Dict[str, object]:
    try:
        return _parse_llm_response(raw)
    except GenericAnalysisError:
        repaired = await _repair_json_with_utility(raw, role=LLMRole.ANALYSIS_PRIMARY)
        if repaired:
            try:
                return _parse_llm_response(repaired)
            except GenericAnalysisError as exc:
                logger.warning(
                    "generic_analysis.json_repair_failed raw_preview=%r repaired_preview=%r error=%s",
                    (raw or "")[:300],
                    repaired[:300],
                    exc,
                )
        raise


def _assemble_result(
    payload: Dict[str, object],
    *,
    mission_id: int,
    document_ids: List[int],
    profile: str,
) -> GenericAnalysisResult:
    result_payload = {
        "mission_id": mission_id,
        "document_ids": document_ids,
        "profile": profile,
        "summary": str(payload.get("summary") or ""),
        "key_entities": _normalize_strings(payload.get("key_entities")),
        "key_events": _normalize_strings(payload.get("key_events")),
        "contradictions": _normalize_strings(payload.get("contradictions")),
        "gaps": _normalize_strings(payload.get("gaps")),
        "follow_up_questions": _normalize_followups(payload.get("follow_up_questions")),
        "decision_note": str(payload.get("decision_note") or ""),
    }
    return GenericAnalysisResult(**result_payload)


def _select_system_prompt() -> str:
    return GENERIC_SYSTEM_PROMPT


def _profile_hint(profile: str) -> str:
    return HUMINT_PROFILE_HINT if profile == "humint" else GENERIC_PROFILE_HINT


def _build_user_prompt(profile: str, context: Dict[str, Any]) -> str:
    profile_hint = _profile_hint(profile)
    context_block = json.dumps(context, ensure_ascii=False, indent=2)
    schema_block = (
        "{\n"
        "  \"summary\": string,\n"
        "  \"key_entities\": string[],\n"
        "  \"key_events\": string[],\n"
        "  \"contradictions\": string[],\n"
        "  \"gaps\": string[],\n"
        "  \"follow_up_questions\": [{\"target\": string, \"question\": string}],\n"
        "  \"decision_note\": string\n"
        "}"
    )

    return f"""
{profile_hint}

You are given structured context in JSON format, including mission metadata, the selected
documents, knowledge-graph highlights, and recent mission signals.

Your tasks:

1) SUMMARY:
   - Provide a concise overall summary (2–5 sentences) of the situation.

2) KEY_ENTITIES:
   - List key entities (people, organizations, locations, or key objects) as short strings.

3) KEY_EVENTS:
   - List key events as short phrases.

4) CONTRADICTIONS:
   - List conflicting statements or claims across the documents.
   - If none, return an empty list [] (do NOT write "No contradictions").

5) GAPS:
   - List important missing information or uncertainties that matter for understanding the
     situation or making decisions.

6) FOLLOW_UP_QUESTIONS:
   - Provide objects with two fields: target (who should answer) and question (the question
     text). One question per object.

7) DECISION_NOTE:
   - Provide 1–3 sentences of decision-focused guidance for a supervisor or commander.

Return ONLY valid JSON matching this schema:
{schema_block}

Do NOT add extra fields. Do NOT wrap the JSON in markdown.

CONTEXT (JSON):
{context_block}
""".strip()


def _looks_like_plaintext_response(raw: str | None) -> bool:
    if not raw:
        return True
    text = raw.strip()
    return not any(ch in text for ch in ("{", "["))


def _build_retry_prompt(user_prompt: str, previous_output: str | None) -> str:
    preview = (previous_output or "").strip()
    if len(preview) > 1200:
        preview = f"{preview[:1200]}…"
    return (
        "Your previous reply was rejected because it was NOT valid JSON. "
        "You must now respond ONLY with a JSON object that matches the schema exactly. "
        "Do not include explanations, markdown, or commentary.\n\n"
        "Earlier invalid reply (for reference, do NOT copy it):\n"
        f"{preview}\n\n"
        "Redo the task now, following the original instructions below.\n\n"
        f"{user_prompt}"
    )


async def run_generic_analysis(req: GenericAnalysisRequest) -> GenericAnalysisResult:
    session = _get_session()
    try:
        mission = _snapshot_mission(session, req.mission_id)
        documents = _snapshot_documents(session, mission.id, req.document_ids)
        analysis_context = _build_analysis_context(session, mission, documents)
    finally:
        session.close()

    system_prompt = _select_system_prompt()
    user_prompt = _build_user_prompt(req.profile, analysis_context)
    try:
        raw_response = await call_llm_with_role(
            prompt=user_prompt,
            system=system_prompt,
            policy_block=STRICT_JSON_POLICY_BLOCK,
            role=LLMRole.ANALYSIS_PRIMARY,
        )
    except LLMCallException as exc:
        logger.exception("generic_analysis.llm_failure", extra={"mission_id": req.mission_id})
        raise GenericAnalysisError("LLM analysis failed") from exc

    try:
        payload = await _parse_or_repair_response(raw_response)
    except GenericAnalysisError:
        if _looks_like_plaintext_response(raw_response):
            logger.warning("generic_analysis.retrying_plaintext_response", extra={"mission_id": req.mission_id})
            retry_prompt = _build_retry_prompt(user_prompt, raw_response)
            try:
                raw_response = await call_llm_with_role(
                    prompt=retry_prompt,
                    system=system_prompt,
                    policy_block=STRICT_JSON_POLICY_BLOCK,
                    role=LLMRole.ANALYSIS_PRIMARY,
                )
            except LLMCallException as exc:
                logger.exception("generic_analysis.retry_llm_failure", extra={"mission_id": req.mission_id})
                raise GenericAnalysisError("LLM analysis failed") from exc
            payload = await _parse_or_repair_response(raw_response)
        else:
            raise

    return _assemble_result(
        payload,
        mission_id=req.mission_id,
        document_ids=req.document_ids,
        profile=req.profile,
    )
