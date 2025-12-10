from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
import re
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.authorities import AuthorityType, get_descriptor
from app.services import (
    authority_history,
    extraction_service,
    guardrail_service,
    llm_client,
)
from app.services.aggregator_client import AggregatorClient, AggregatorClientError
from app.services.prompt_builder import build_global_system_prompt


logger = logging.getLogger(__name__)
_aggregator_client = AggregatorClient()


FACTS_TASK_INSTRUCTIONS = """
You are an intelligence analysis assistant. Extract raw factual statements from the mission sources and knowledge graph.
- Do not include hypotheticals, speculation, or recommendations.
- Prefer concise, atomic statements (who/what/when/where/how).
- Respect all authority and INT guardrails included in this system prompt.
""".strip()

INFORMATION_GAPS_TASK_INSTRUCTIONS = """
You are reviewing the mission to identify information gaps.
- Highlight missing or weak INT coverage, specifying INT types or time windows.
- Call out entities or events that lack sufficient corroboration.
- Use knowledge graph metrics to flag areas that are too sparse for confident analysis.
- Separate evidence-backed findings from speculative gaps and respect all guardrails.
""".strip()

CROSS_DOC_TASK_INSTRUCTIONS = """
You are performing cross-document and cross-source analysis.
- Surface corroborated findings, contradictions, and notable trends.
- Cite only what is supported by the mission context or knowledge graph.
- Respect authority and INT constraints.
""".strip()

ANALYSIS_GUARDRAIL_RULES_BODY = """
You will receive structured JSON describing the mission authority, entities, events, and knowledge-graph highlights.
You MUST:
- Use ONLY the information in that JSON.
- NOT invent incidents, locations, agencies, subjects, vehicles, or organizations that are not present in the JSON.
- NOT invent named groups or describe the mission as "Federal" unless the JSON explicitly says so.
- If information is missing, explicitly note the gap with 'None available'.
- Never mention JSON, 'context', 'mission text', or 'Agent Run Advisory' in your response.
- Do not reference variable names (e.g., evidence.incidents[0], Event ID 3) or describe what inputs you received.
- Write as a final, human analyst product—no meta narration.
""".strip()

ESTIMATE_TASK_BODY = """
Produce a 2-3 paragraph operational estimate covering situation, threat/adversary posture, friendly considerations, and risk. Ground every statement in available documents or the knowledge graph and call out limitations if coverage is sparse.
""".strip()

SUMMARY_TASK_BODY = """
Provide a concise narrative (<=120 words) focused on intent, capability, and risk.
""".strip()

NEXT_STEPS_TASK_BODY = """
Recommend 3-7 concrete follow-up actions (collection, coordination, verification, tasking). Ensure each action is legal for the current authority and INT set, and tie it to identified gaps.
""".strip()


def build_authority_role_text(authority_value: str | AuthorityType | None) -> str:
    """Return an authority-aware role description for the analyst prompts."""

    descriptor = get_descriptor(authority_value)
    authority = descriptor.value

    if authority == AuthorityType.TITLE_50_IC:
        return (
            "You are an intelligence analyst operating under Title 50 foreign intelligence authorities. "
            "Focus on HUMINT and all-source analysis, collection guidance, and decision support—not criminal prosecution. "
            "Do NOT recommend arrests, search warrants, indictments, or other domestic law-enforcement actions."
        )
    if authority == AuthorityType.LEO:
        return (
            "You are an intelligence analyst supporting a law-enforcement investigative mission. "
            "Provide evidence-focused insights that inform investigators, but do not direct tactical teams or promise prosecutorial outcomes."
        )
    return (
        f"You are an intelligence analyst supporting the {descriptor.label} authority lane. "
        "Align all findings and recommendations with that mission scope and legal framework."
    )


def build_analysis_guardrail_rules(authority_value: str | AuthorityType | None) -> str:
    role_text = build_authority_role_text(authority_value)
    descriptor = get_descriptor(authority_value)
    extra_lines: list[str] = []

    if descriptor.value == AuthorityType.TITLE_50_IC:
        extra_lines.append(
            "- Never reference domestic criminal procedure (probable cause, warrants, indictments) or request arrests. Keep recommendations framed as collection, analysis, or interagency coordination."
        )
    elif descriptor.value == AuthorityType.LEO:
        extra_lines.append(
            "- Discuss investigative steps, legal process, and coordination needs, but always distinguish intelligence recommendations from operational orders."
        )
    else:
        extra_lines.append(
            "- Keep every statement within the mission's stated authority and INT set, noting when additional authorities or partners would be required."
        )

    extra_text = "\n".join(extra_lines)
    body = ANALYSIS_GUARDRAIL_RULES_BODY if not extra_text else f"{ANALYSIS_GUARDRAIL_RULES_BODY}\n{extra_text}"
    return f"{role_text}\n{body}".strip()


def build_estimate_task_instructions(authority_value: str | AuthorityType | None) -> str:
    guardrails = build_analysis_guardrail_rules(authority_value)
    return f"{guardrails}\n{ESTIMATE_TASK_BODY}".strip()


def build_summary_task_instructions(authority_value: str | AuthorityType | None) -> str:
    guardrails = build_analysis_guardrail_rules(authority_value)
    return f"{guardrails}\n{SUMMARY_TASK_BODY}".strip()


def build_next_steps_task_instructions(authority_value: str | AuthorityType | None) -> str:
    guardrails = build_analysis_guardrail_rules(authority_value)
    return f"{guardrails}\n{NEXT_STEPS_TASK_BODY}".strip()

SELF_VERIFY_TASK_INSTRUCTIONS = """
You are reviewing the analytic output for internal consistency and quality.
- Identify contradictions, weak sourcing, or logical gaps.
- Provide notes on any deficiencies while respecting guardrails.
""".strip()

DELTA_TASK_INSTRUCTIONS = """
You are comparing the previous agent run with the current one.
- Describe what is new, unchanged, or escalating.
- Reference events and findings from mission context and the knowledge graph only.
""".strip()


def _parse_timestamp(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _normalize_name(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_title(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _coerce_location(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value if item]
        return "; ".join(part for part in parts if part) or None
    if isinstance(value, dict):
        name = value.get("name") if isinstance(value.get("name"), str) else None
        return name or (str(value).strip() or None)
    coerced = str(value).strip()
    return coerced or None


def _build_mission_context(mission: models.Mission, documents: List[models.Document]) -> str:
    sections: List[str] = []

    filtered_documents = [
        doc for doc in documents if getattr(doc, "include_in_analysis", True)
    ]

    mission_header = [f"Mission: {mission.name}"]
    if mission.description:
        mission_header.append(f"Description: {mission.description.strip()}")
    sections.append("\n".join(mission_header))

    for idx, doc in enumerate(filtered_documents, start=1):
        doc_lines = [f"Document {idx}:"]
        if doc.title:
            doc_lines.append(f"Title: {doc.title}")
        if doc.created_at:
            doc_lines.append(f"Timestamp: {doc.created_at.isoformat()}")
        content = (doc.content or "").strip()
        if content:
            doc_lines.append("Content:")
            doc_lines.append(content)
        sections.append("\n".join(doc_lines))

    return "\n\n".join(section for section in sections if section.strip())


def _build_prompt_context(
    mission: models.Mission,
    history_payload: Dict[str, Any],
    *,
    kg_warnings: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "authority": mission.mission_authority,
        "int_types": list(mission.int_types or []),
        "authority_history": history_payload.get("entries") or [],
        "mission": {
            "id": mission.id,
            "name": mission.name,
            "mission_authority": mission.mission_authority,
            "int_types": list(mission.int_types or []),
            "authority_history": history_payload.get("entries") or [],
            "created_at": mission.created_at.isoformat() if mission.created_at else None,
        },
    }


def _build_analysis_corpus(
    mission: models.Mission,
    documents: List[models.Document],
    entities: List[models.Entity],
    events: List[models.Event],
) -> str:
    parts: List[str] = [
        mission.name or "",
        mission.description or "",
        mission.mission_authority or "",
        mission.original_authority or "",
    ]
    for doc in documents:
        parts.extend(filter(None, [getattr(doc, "title", None), getattr(doc, "content", None)]))
    for entity in entities:
        parts.extend(filter(None, [getattr(entity, "name", None), getattr(entity, "description", None)]))
    for event in events:
        parts.extend(
            filter(
                None,
                [
                    getattr(event, "title", None),
                    getattr(event, "summary", None),
                    getattr(event, "location", None),
                ],
            )
        )
    return " \n".join(parts).lower()


def _sanitize_analysis_text(text: str | None, mission: models.Mission, source_corpus: str) -> str | None:
    if not text:
        return text
    sanitized = text

    def _replace(pattern: str, replacement: str) -> None:
        nonlocal sanitized
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    meta_phrases = [
        "provided mission text",
        "provided mission",
        "provided json",
        "provided entities",
        "provided events",
        "provided context",
        "mission text",
        "context outlines",
        "agent run advisory",
        "based on the provided",
        "in the provided",
    ]
    for phrase in meta_phrases:
        _replace(re.escape(phrase), "")

    _replace(r"event id\s*\d+", "")
    _replace(r"evidence\.[a-zA-Z0-9_]+\[[0-9]+\]", "")

    authority = (mission.mission_authority or "").strip()
    if authority.upper() == "LEO":
        _replace(r"federal law enforcement", authority.title())
        _replace(r"federal", authority.title())

    if "city hall" in sanitized.lower() and "city hall" not in source_corpus:
        _replace(r"city hall", "local government facility")

    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized

    kg_summary = None
    if mission.kg_namespace:
        try:
            kg_summary = _aggregator_client.get_graph_summary(mission.kg_namespace)
        except AggregatorClientError:
            logger.warning(
                "Failed to fetch KG summary for mission %s (namespace=%s)",
                mission.id,
                mission.kg_namespace,
                exc_info=True,
            )
            if kg_warnings is not None:
                kg_warnings.append(
                    {
                        "type": "kg_unavailable",
                        "message": f"Knowledge graph summary unavailable for namespace={mission.kg_namespace}",
                    }
                )

    if isinstance(kg_summary, dict):
        context["kg_summary"] = kg_summary
        context["mission"]["kg_summary"] = kg_summary

    return context


def _build_facts_system_prompt(prompt_context: Dict[str, Any]) -> str:
    return build_global_system_prompt(prompt_context, FACTS_TASK_INSTRUCTIONS)


def _build_gaps_system_prompt(prompt_context: Dict[str, Any]) -> str:
    return build_global_system_prompt(prompt_context, INFORMATION_GAPS_TASK_INSTRUCTIONS)


def _build_cross_doc_system_prompt(prompt_context: Dict[str, Any]) -> str:
    return build_global_system_prompt(prompt_context, CROSS_DOC_TASK_INSTRUCTIONS)


def _build_estimate_system_prompt(
    prompt_context: Dict[str, Any], authority_value: str | AuthorityType | None
) -> str:
    instructions = build_estimate_task_instructions(authority_value)
    return build_global_system_prompt(prompt_context, instructions)


def _build_summary_system_prompt(
    prompt_context: Dict[str, Any], authority_value: str | AuthorityType | None
) -> str:
    instructions = build_summary_task_instructions(authority_value)
    return build_global_system_prompt(prompt_context, instructions)


def _build_next_steps_system_prompt(
    prompt_context: Dict[str, Any], authority_value: str | AuthorityType | None
) -> str:
    instructions = build_next_steps_task_instructions(authority_value)
    return build_global_system_prompt(prompt_context, instructions)


def _build_self_verify_system_prompt(prompt_context: Dict[str, Any]) -> str:
    return build_global_system_prompt(prompt_context, SELF_VERIFY_TASK_INSTRUCTIONS)


def _build_delta_system_prompt(prompt_context: Dict[str, Any]) -> str:
    return build_global_system_prompt(prompt_context, DELTA_TASK_INSTRUCTIONS)


def _entity_to_dict(entity: models.Entity) -> dict:
    return {
        "id": entity.id,
        "mission_id": entity.mission_id,
        "name": entity.name,
        "type": entity.type,
        "description": entity.description,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
    }


def _event_to_dict(event: models.Event) -> dict:
    return {
        "id": event.id,
        "mission_id": event.mission_id,
        "title": event.title,
        "summary": event.summary,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "location": event.location,
        "involved_entity_ids": event.involved_entity_ids or [],
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def _ingest_structured_graph_payload(
    mission: models.Mission,
    entities: List[Dict],
    events: List[Dict],
    *,
    profile: str,
) -> None:
    if not mission.kg_namespace:
        return
    if not entities and not events:
        return

    payload = {
        "kind": "structured_entities_events",
        "mission_id": mission.id,
        "mission_name": mission.name,
        "profile": profile,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "entities": entities,
        "events": events,
    }
    history_payload = authority_history.build_authority_history_payload(mission)
    metadata = {
        "source": "apex_agent_cycle",
        "mission_id": mission.id,
        "mission_authority": mission.mission_authority,
        "int_types": list(mission.int_types or []),
        "profile": profile,
        "original_authority": mission.original_authority,
        "authority_history": history_payload["lines"],
    }

    try:
        _aggregator_client.ingest_json_payload(
            mission.kg_namespace,
            title=f"structured-extract-{mission.id}",
            payload=payload,
            metadata=metadata,
        )
    except AggregatorClientError:
        logger.warning(
            "Failed to ingest structured KG payload",
            exc_info=True,
            extra={"mission_id": mission.id},
        )


async def run_agent_cycle(mission_id: int, db: Session, profile: str = "humint") -> models.AgentRun:
    """Execute the end-to-end APEX agent cycle for a mission."""

    try:
        profile_enum = extraction_service.AnalysisProfile(profile)
    except ValueError:
        profile_enum = extraction_service.AnalysisProfile.HUMINT

    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")

    documents = (
        db.query(models.Document)
        .filter(models.Document.mission_id == mission_id)
        .order_by(models.Document.created_at.asc())
        .all()
    )

    history_payload = authority_history.build_authority_history_payload(mission)
    kg_warning_issues: List[Dict[str, str]] = []
    prompt_context = _build_prompt_context(mission, history_payload, kg_warnings=kg_warning_issues)
    facts_system_prompt = _build_facts_system_prompt(prompt_context)
    gaps_system_prompt = _build_gaps_system_prompt(prompt_context)
    cross_doc_system_prompt = _build_cross_doc_system_prompt(prompt_context)
    authority_value = mission.mission_authority
    estimate_system_prompt = _build_estimate_system_prompt(prompt_context, authority_value)
    summary_system_prompt = _build_summary_system_prompt(prompt_context, authority_value)
    next_steps_system_prompt = _build_next_steps_system_prompt(prompt_context, authority_value)
    self_verify_system_prompt = _build_self_verify_system_prompt(prompt_context)
    delta_system_prompt = _build_delta_system_prompt(prompt_context)
    mission_context = _build_mission_context(mission, documents)
    facts = (
        await llm_client.extract_raw_facts(
            mission_context,
            profile=profile_enum.value,
            policy_block=facts_system_prompt,
        )
        if mission_context
        else []
    )

    entities_payload, events_payload = await extraction_service.extract_entities_and_events_for_mission(
        mission,
        documents,
        profile=profile_enum.value,
    )

    _ingest_structured_graph_payload(
        mission,
        entities_payload,
        events_payload,
        profile=profile_enum.value,
    )

    existing_entities = (
        db.query(models.Entity)
        .filter(models.Entity.mission_id == mission.id)
        .all()
    )
    entity_map: Dict[str, models.Entity] = {
        _normalize_name(entity.name): entity for entity in existing_entities if entity.name
    }

    created_entities: List[models.Entity] = []

    for entity_payload in entities_payload:
        raw_name = entity_payload.get("name") or ""
        normalized_name = _normalize_name(raw_name)
        if not normalized_name:
            continue

        existing_entity = entity_map.get(normalized_name)
        description = entity_payload.get("description")
        type_hint = entity_payload.get("type")

        if existing_entity:
            current_desc = existing_entity.description or ""
            if description and len(description) > len(current_desc):
                existing_entity.description = description
            if type_hint and not existing_entity.type:
                existing_entity.type = type_hint
            continue

        entity_model = models.Entity(
            mission_id=mission.id,
            name=raw_name.strip(),
            type=type_hint,
            description=description,
        )
        db.add(entity_model)
        created_entities.append(entity_model)
        entity_map[normalized_name] = entity_model

    existing_events = (
        db.query(models.Event)
        .filter(models.Event.mission_id == mission.id)
        .all()
    )
    previous_event_dicts = [_event_to_dict(event) for event in existing_events]

    def _normalize_ts(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.replace(microsecond=0)

    existing_event_keys = {
        (
            _normalize_title(event.title),
            _normalize_ts(event.timestamp),
        )
        for event in existing_events
    }

    created_events: List[models.Event] = []
    for event_payload in events_payload:
        raw_title = event_payload.get("title") or ""
        normalized_title = _normalize_title(raw_title)
        if not normalized_title:
            continue

        timestamp = _normalize_ts(_parse_timestamp(event_payload.get("timestamp")))
        key = (normalized_title, timestamp)
        if key in existing_event_keys:
            continue

        raw_location = event_payload.get("location")
        location_value = _coerce_location(raw_location)

        involved_ids = event_payload.get("involved_entity_ids")
        if involved_ids is None:
            involved_ids_serialized = json.dumps([])
        elif isinstance(involved_ids, str):
            involved_ids_serialized = involved_ids
        else:
            involved_ids_serialized = json.dumps(involved_ids)

        event_model = models.Event(
            mission_id=mission.id,
            title=raw_title.strip(),
            summary=event_payload.get("summary"),
            timestamp=timestamp,
            location=location_value,
            involved_entity_ids=involved_ids_serialized,
        )
        db.add(event_model)
        created_events.append(event_model)
        existing_event_keys.add(key)

    db.commit()

    for record in [*created_entities, *created_events]:
        db.refresh(record)

    entities = (
        db.query(models.Entity)
        .filter(models.Entity.mission_id == mission.id)
        .order_by(models.Entity.created_at.asc())
        .all()
    )
    events = (
        db.query(models.Event)
        .filter(models.Event.mission_id == mission.id)
        .order_by(models.Event.timestamp.is_(None), models.Event.timestamp.asc())
        .all()
    )

    entity_dicts = [_entity_to_dict(entity) for entity in entities]
    event_dicts = [_event_to_dict(event) for event in events]
    analysis_corpus = _build_analysis_corpus(mission, documents, entities, events)

    gaps_result = await llm_client.detect_information_gaps(
        facts,
        entity_dicts,
        event_dicts,
        profile=profile,
        policy_block=gaps_system_prompt,
    )
    gaps = gaps_result.get("gaps", [])

    cross_analysis = await llm_client.cross_document_analysis(
        facts,
        entity_dicts,
        event_dicts,
        profile=profile,
        policy_block=cross_doc_system_prompt,
    )

    operational_estimate = await llm_client.generate_operational_estimate(
        facts,
        entity_dicts,
        event_dicts,
        profile=profile,
        policy_block=estimate_system_prompt,
    )
    operational_estimate = _sanitize_analysis_text(operational_estimate, mission, analysis_corpus)

    summary_core = await llm_client.summarize_mission(
        entity_dicts,
        event_dicts,
        profile=profile,
        policy_block=summary_system_prompt,
    )
    summary_core = _sanitize_analysis_text(summary_core, mission, analysis_corpus)

    cross_sections = []
    if cross_analysis:
        mapping = {
            "corroborated_findings": "Corroborated Findings",
            "contradictions": "Contradictions",
            "notable_trends": "Notable Trends",
        }
        for key, label in mapping.items():
            entries = cross_analysis.get(key) if isinstance(cross_analysis, dict) else None
            if not entries:
                continue
            bullet_lines = "\n".join(f"- {entry}" for entry in entries if str(entry).strip())
            if bullet_lines:
                cross_sections.append(f"{label}:\n{bullet_lines}")

    summary_parts = [summary_core.strip(), f"Operational Estimate:\n{operational_estimate}".strip()]
    if cross_sections:
        summary_parts.append("Cross-Document Insights:\n" + "\n".join(cross_sections))
    summary = "\n\n".join(part for part in summary_parts if part)
    summary = _sanitize_analysis_text(summary, mission, analysis_corpus)
    next_steps = await llm_client.suggest_next_steps(
        entity_dicts,
        event_dicts,
        profile=profile,
        policy_block=next_steps_system_prompt,
    )
    next_steps = _sanitize_analysis_text(next_steps, mission, analysis_corpus)

    verification = await llm_client.self_verify_assessment(
        facts,
        entity_dicts,
        event_dicts,
        summary_core,
        operational_estimate,
        profile=profile,
        policy_block=self_verify_system_prompt,
    )

    previous_run = (
        db.query(models.AgentRun)
        .filter(models.AgentRun.mission_id == mission.id)
        .order_by(models.AgentRun.created_at.desc())
        .first()
    )
    previous_summary = previous_run.summary if previous_run else None
    delta_summary = await llm_client.generate_run_delta(
        previous_summary,
        previous_event_dicts,
        summary_core,
        event_dicts,
        policy_block=delta_system_prompt,
    )

    guardrail_service.set_guardrail_context(has_docs=bool(documents))
    history_lines = history_payload["lines"]
    has_pivots = any(entry.get("type") == "pivot" for entry in history_payload["entries"])
    guardrail_metadata = {
        "original_authority": mission.original_authority,
        "current_authority": mission.mission_authority,
        "has_pivots": has_pivots,
    }
    base_guardrail = guardrail_service.run_guardrails(
        summary,
        next_steps,
        authority=mission.mission_authority,
        authority_history=history_lines,
        authority_metadata=guardrail_metadata,
    )
    analytic_guardrail = await guardrail_service.evaluate_guardrails(
        facts=facts,
        entities=entity_dicts,
        events=event_dicts,
        estimate=operational_estimate,
        summary=summary,
        gaps=gaps_result,
        cross=cross_analysis,
        profile=profile,
        authority=mission.mission_authority,
        policy_block=summary_system_prompt,
        authority_history=history_lines,
        authority_metadata=guardrail_metadata,
    )
    analytic_status = analytic_guardrail["status"]
    analytic_issues = analytic_guardrail.get("issues", [])

    status_rank = {"ok": 0, "warning": 1, "blocked": 2}
    analytic_rank = {"OK": 0, "CAUTION": 1, "REVIEW": 2}

    final_status = base_guardrail.get("status", "ok")
    final_issues: List[Any] = list(base_guardrail.get("issues", []))
    base_rank = status_rank.get(final_status, 1)

    if analytic_issues:
        final_issues.extend(f"Analytic Review: {issue}" for issue in analytic_issues)

    analytic_status_upper = (analytic_status or "OK").upper()
    analytic_score = analytic_rank.get(analytic_status_upper, 2)
    if analytic_score > base_rank:
        final_status = "warning" if analytic_score == 1 else "blocked"
        base_rank = analytic_score if analytic_score <= 2 else base_rank

    consistency = (verification.get("internal_consistency") or "good").lower()
    if consistency in {"questionable", "poor"}:
        final_issues.append(f"Self-check: internal consistency rated {consistency}.")
        escalation = 1 if consistency == "questionable" else 2
        if escalation > base_rank:
            final_status = "warning" if escalation == 1 else "blocked"
            base_rank = escalation

    adj = verification.get("confidence_adjustment")
    if isinstance(adj, (int, float)) and abs(adj) > 0:
        final_issues.append(f"Self-check confidence adjustment: {adj:+.2f}")

    for note in verification.get("notes", []) or []:
        note_text = str(note).strip()
        if note_text:
            final_issues.append(f"Self-check note: {note_text}")

    agent_status = "completed"
    if final_status == "blocked":
        agent_status = "failed"

    if kg_warning_issues:
        final_issues.extend(kg_warning_issues)

    agent_run = models.AgentRun(
        mission_id=mission.id,
        status=agent_status,
        summary=summary,
        next_steps=next_steps,
        guardrail_status=final_status,
        guardrail_issues=final_issues,
    )

    agent_run.raw_facts = facts
    agent_run.gaps = gaps
    agent_run.delta_summary = delta_summary

    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)

    return agent_run
