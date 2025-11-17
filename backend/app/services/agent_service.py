from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.services import extraction_service, guardrail_service, llm_client


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


async def run_agent_cycle(mission_id: int, db: Session, profile: str = "humint") -> models.AgentRun:
    """Execute the end-to-end APEX agent cycle for a mission."""

    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")

    documents = (
        db.query(models.Document)
        .filter(models.Document.mission_id == mission_id)
        .order_by(models.Document.created_at.asc())
        .all()
    )

    mission_context = _build_mission_context(mission, documents)
    facts = await llm_client.extract_raw_facts(mission_context, profile=profile) if mission_context else []

    entities_payload, events_payload = await extraction_service.extract_entities_and_events_for_mission(
        mission,
        documents,
        profile=profile,
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

        event_model = models.Event(
            mission_id=mission.id,
            title=raw_title.strip(),
            summary=event_payload.get("summary"),
            timestamp=timestamp,
            location=event_payload.get("location"),
            involved_entity_ids=event_payload.get("involved_entity_ids", []),
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

    gaps_result = await llm_client.detect_information_gaps(
        facts,
        entity_dicts,
        event_dicts,
        profile=profile,
    )
    gaps = gaps_result.get("gaps", [])

    cross_analysis = await llm_client.cross_document_analysis(
        facts,
        entity_dicts,
        event_dicts,
        profile=profile,
    )

    operational_estimate = await llm_client.generate_operational_estimate(
        facts,
        entity_dicts,
        event_dicts,
        profile=profile,
    )

    summary_core = await llm_client.summarize_mission(entity_dicts, event_dicts, profile=profile)

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
    next_steps = await llm_client.suggest_next_steps(entity_dicts, event_dicts, profile=profile)

    verification = await llm_client.self_verify_assessment(
        facts,
        entity_dicts,
        event_dicts,
        summary_core,
        operational_estimate,
        profile=profile,
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
    )

    guardrail_service.set_guardrail_context(has_docs=bool(documents))
    base_guardrail = guardrail_service.run_guardrails(summary, next_steps)
    analytic_status, analytic_issues = await guardrail_service.evaluate_guardrails(
        facts=facts,
        entities=entity_dicts,
        events=event_dicts,
        estimate=operational_estimate,
        summary=summary,
        gaps=gaps_result,
        cross=cross_analysis,
        profile=profile,
    )

    status_rank = {"ok": 0, "warning": 1, "blocked": 2}
    analytic_rank = {"OK": 0, "CAUTION": 1, "REVIEW": 2}

    final_status = base_guardrail.get("status", "ok")
    final_issues = list(base_guardrail.get("issues", []))
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

    agent_run = models.AgentRun(
        mission_id=mission.id,
        status=agent_status,
        summary=summary,
        next_steps=next_steps,
        guardrail_status=final_status,
        guardrail_issues=final_issues,
    )

    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)

    # attach transient analysis artifacts (not yet stored in DB columns)
    agent_run.raw_facts = facts
    agent_run.gaps = gaps
    agent_run.delta_summary = delta_summary

    return agent_run
