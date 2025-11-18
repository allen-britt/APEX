"""Reporting dataset assembly utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app import models, schemas

def _format_datetime(value: Optional[datetime]) -> str:
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()

def _mission_payload(mission: models.Mission) -> schemas.ApexMissionPayload:
    return schemas.ApexMissionPayload(
        id=mission.id,
        title=mission.name,
        description=mission.description,
        status="active",
        priority="",
        theater="",
        created_at=_format_datetime(mission.created_at),
        updated_at=_format_datetime(mission.updated_at),
        tags=[],
        commander_intent=None,
    )

def _document_payload(doc: models.Document) -> schemas.ApexDocumentPayload:
    return schemas.ApexDocumentPayload(
        id=doc.id,
        title=doc.title or "Untitled document",
        source_type="OTHER",
        origin=None,
        created_at=_format_datetime(doc.created_at),
        ingested_at=None,
        include_in_analysis=bool(doc.include_in_analysis),
        classification=None,
    )

def _entity_payload(entity: models.Entity) -> schemas.ApexEntityPayload:
    return schemas.ApexEntityPayload(
        id=entity.id,
        name=entity.name,
        type=entity.type or "unknown",
        role=entity.description,
        confidence=None,
        tags=[],
        first_seen=_format_datetime(entity.created_at),
        last_seen=_format_datetime(entity.created_at),
    )

def _event_payload(event: models.Event) -> schemas.ApexEventPayload:
    return schemas.ApexEventPayload(
        id=event.id,
        title=event.title,
        description=event.summary,
        timestamp=_format_datetime(event.timestamp),
        location=event.location,
        actors=[int(pk) for pk in (event.involved_entity_ids or []) if isinstance(pk, int)],
        confidence=None,
        phase=None,
    )

def _agent_run_payload(run: Optional[models.AgentRun]) -> schemas.ApexAgentRunPayload:
    if not run:
        now = datetime.now(timezone.utc)
        return schemas.ApexAgentRunPayload(
            id=None,
            status="pending",
            created_at=_format_datetime(now),
            profile=None,
            summary=None,
            next_steps=None,
            operational_estimate=None,
            raw_facts=None,
            gaps=None,
            delta_summary=None,
        )

    return schemas.ApexAgentRunPayload(
        id=run.id,
        status=run.status,
        created_at=_format_datetime(run.created_at),
        profile=getattr(run, "profile", None),
        summary=run.summary,
        next_steps=run.next_steps,
        operational_estimate=getattr(run, "operational_estimate", None),
        raw_facts=None,
        gaps=None,
        delta_summary=getattr(run, "delta_summary", None),
    )

def build_report_dataset(
    mission: models.Mission,
    documents: List[models.Document],
    entities: List[models.Entity],
    events: List[models.Event],
    run: Optional[models.AgentRun],
    *,
    insights: Optional[Dict[str, List[str]]] = None,
    guardrail: Optional[schemas.GuardrailReport] = None,
    generator_version: str = "unknown",
    model_name: Optional[str] = None,
) -> schemas.ApexReportDataset:
    mission_payload = _mission_payload(mission)
    documents_payload = [_document_payload(doc) for doc in documents]
    entities_payload = [_entity_payload(entity) for entity in entities]
    events_payload = [_event_payload(event) for event in events]
    agent_run_payload = _agent_run_payload(run)

    cross_insights = schemas.ApexCrossDocumentInsights(**(insights or {}))
    guardrails_payload = None
    if guardrail:
        guardrails_payload = schemas.ApexGuardrailStatus(
            heuristic_score=guardrail.overall_score,
            analytic_score=None,
            issues=guardrail.issues,
            notes=None,
        )

    meta_payload = schemas.ApexReportMeta(
        generated_at=_format_datetime(datetime.now(timezone.utc)),
        generator_version=generator_version,
        model_name=model_name,
        template=None,
    )

    return schemas.ApexReportDataset(
        mission=mission_payload,
        documents=documents_payload,
        entities=entities_payload,
        events=events_payload,
        agent_run=agent_run_payload,
        cross_doc_insights=cross_insights,
        guardrails=guardrails_payload,
        meta=meta_payload,
        delta=None,
    )
