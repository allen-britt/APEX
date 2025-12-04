from __future__ import annotations

import json
import logging
from typing import Iterable, List

from sqlalchemy.orm import Session

from app import models
from app.models.evidence import (
    EvidenceBundle,
    EvidenceDocument,
    EvidenceEvent,
    EvidenceGap,
    EvidenceIncident,
    EvidenceLocation,
    EvidenceSubject,
)
from app.services.aggregator_client import AggregatorClient, AggregatorClientError

logger = logging.getLogger(__name__)


class EvidenceExtractorService:
    """Builds structured evidence bundles for missions without invoking LLMs."""

    def __init__(self, session: Session, *, aggregator_client: AggregatorClient | None = None) -> None:
        self.session = session
        self._aggregator = aggregator_client or AggregatorClient()

    def build_evidence_bundle(self, mission_id: int) -> EvidenceBundle:
        mission = (
            self.session.query(models.Mission)
            .filter(models.Mission.id == mission_id)
            .first()
        )
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        incidents = self._build_incidents(mission.events or [])
        subjects = self._build_subjects(mission.entities or [])
        documents = self._build_documents(mission.documents or [])
        events = self._build_events(mission.events or [])
        gaps = self._build_gaps(mission.gap_analysis)

        kg_summary = self._get_kg_summary(mission)

        bundle = EvidenceBundle(
            mission_id=str(mission.id),
            mission_name=mission.name,
            authority=mission.mission_authority,
            int_lanes=list(mission.int_types or []),
            incidents=incidents,
            subjects=subjects,
            associates=[],
            locations=[],
            events=events,
            documents=documents,
            gaps=gaps,
            kg_snapshot_summary=kg_summary,
        )

        return bundle

    def _build_incidents(self, events: Iterable[models.Event]) -> List[EvidenceIncident]:
        incident_list: List[EvidenceIncident] = []
        for event in events:
            incident_list.append(
                EvidenceIncident(
                    id=str(event.id),
                    summary=event.summary or event.title,
                    location=event.location,
                    occurred_at=event.timestamp.isoformat() if event.timestamp else None,
                    source_ids=[str(event.id)],
                )
            )
        return incident_list

    def _build_subjects(self, entities: Iterable[models.Entity]) -> List[EvidenceSubject]:
        subject_list: List[EvidenceSubject] = []
        for entity in entities:
            subject_list.append(
                EvidenceSubject(
                    id=str(entity.id),
                    name=entity.name,
                    type=entity.type,
                    description=entity.description,
                )
            )
        return subject_list

    def _build_documents(self, documents: Iterable[models.Document]) -> List[EvidenceDocument]:
        document_list: List[EvidenceDocument] = []
        for doc in documents:
            document_list.append(
                EvidenceDocument(
                    id=str(doc.id),
                    title=doc.title or "Mission Document",
                )
            )
        return document_list

    def _build_events(self, events: Iterable[models.Event]) -> List[EvidenceEvent]:
        event_list: List[EvidenceEvent] = []
        for event in events:
            event_list.append(
                EvidenceEvent(
                    id=str(event.id),
                    type=None,
                    description=event.summary or event.title,
                    occurred_at=event.timestamp.isoformat() if event.timestamp else None,
                    location_id=None,
                )
            )
        return event_list

    def _build_gaps(self, gap_payload) -> List[EvidenceGap]:
        gap_list: List[EvidenceGap] = []
        if isinstance(gap_payload, list):
            source = gap_payload
        elif isinstance(gap_payload, dict):
            source = [item for value in gap_payload.values() if isinstance(value, list) for item in value]
        else:
            source = []

        for idx, gap in enumerate(source):
            if not isinstance(gap, dict):
                continue
            description = gap.get("description") or gap.get("detail")
            if not description:
                continue
            gap_list.append(
                EvidenceGap(
                    id=str(gap.get("id") or idx),
                    description=description,
                    severity=gap.get("severity"),
                )
            )
        return gap_list

    def _get_kg_summary(self, mission: models.Mission) -> str | None:
        if not mission.kg_namespace:
            return None
        try:
            summary = self._aggregator.get_graph_summary(mission.kg_namespace)
        except AggregatorClientError:
            logger.info("Failed to fetch KG summary for mission %s", mission.id, exc_info=True)
            return None
        if isinstance(summary, dict):
            return summary.get("summary") or json.dumps(summary)
        return str(summary)
