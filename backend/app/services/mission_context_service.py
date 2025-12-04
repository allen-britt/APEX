from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from app.services.aggregator_client import AggregatorClient, AggregatorClientError
from app.services.authority_history import build_authority_history_payload
from app.services.namespace_service import ensure_mission_namespace


class MissionContextError(Exception):
    """Raised when the mission context cannot be constructed."""


class MissionContextService:
    def __init__(
        self,
        db: Session,
        *,
        aggregator_client: Optional[AggregatorClient] = None,
    ) -> None:
        self.db = db
        self._aggregator = aggregator_client or AggregatorClient()

    def build_context(self, mission_id: int) -> Dict[str, Any]:
        mission = self.db.query(models.Mission).filter(models.Mission.id == mission_id).first()
        if not mission:
            raise MissionContextError("Mission not found")
        return self.build_context_for_mission(mission)

    def build_context_for_mission(self, mission: models.Mission) -> Dict[str, Any]:
        authority_history = build_authority_history_payload(mission)
        mission_block = {
            "id": mission.id,
            "name": mission.name,
            "description": mission.description,
            "mission_authority": mission.mission_authority,
            "current_authority": mission.mission_authority,
            "original_authority": mission.original_authority,
            "int_types": list(mission.int_types or []),
            "created_at": _isoformat_or_none(mission.created_at),
            "updated_at": _isoformat_or_none(mission.updated_at),
            "authority_history": authority_history["entries"],
            "authority_history_lines": authority_history["lines"],
        }

        documents = self._serialize_documents(mission.id)
        entities = self._serialize_entities(mission.id)
        events = self._serialize_events(mission.id)
        datasets = self._serialize_datasets(mission.id)

        latest_run = self._serialize_latest_agent_run(mission.id)
        if latest_run:
            mission_block["latest_agent_run"] = latest_run

        context: Dict[str, Any] = {
            "mission": mission_block,
            "documents": documents,
            "entities": entities,
            "events": events,
            "datasets": datasets,
            "gap_analysis": mission.gap_analysis if isinstance(mission.gap_analysis, dict) else None,
        }

        if latest_run:
            context["latest_agent_run"] = latest_run

        kg_snapshot = self._fetch_kg_snapshot(mission)
        if kg_snapshot:
            context["kg_snapshot"] = kg_snapshot

        kg_summary = self._fetch_kg_summary(mission)
        if kg_summary:
            context["kg_summary"] = kg_summary
        return context

    def _serialize_latest_agent_run(self, mission_id: int) -> Dict[str, Any] | None:
        run = (
            self.db.query(models.AgentRun)
            .filter(models.AgentRun.mission_id == mission_id)
            .order_by(models.AgentRun.created_at.desc())
            .first()
        )
        if not run:
            return None

        return {
            "id": run.id,
            "status": run.status,
            "summary": run.summary,
            "next_steps": run.next_steps,
            "guardrail_status": run.guardrail_status,
            "guardrail_issues": list(run.guardrail_issues or []),
            "created_at": _isoformat_or_none(run.created_at),
            "updated_at": _isoformat_or_none(run.updated_at),
        }

    def _serialize_documents(self, mission_id: int) -> List[Dict[str, Any]]:
        documents = (
            self.db.query(models.Document)
            .filter(models.Document.mission_id == mission_id)
            .order_by(models.Document.created_at.asc())
            .all()
        )
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "include_in_analysis": doc.include_in_analysis,
                "created_at": _isoformat_or_none(doc.created_at),
            }
            for doc in documents
        ]

    def _fetch_kg_snapshot(self, mission: models.Mission) -> Dict[str, Any] | None:
        if not mission.kg_namespace:
            return None

        try:
            ensure_mission_namespace(mission, db=self.db)
            snapshot = self._aggregator.get_mission_kg_snapshot(
                mission.kg_namespace,
                authority=mission.mission_authority,
                int_types=list(mission.int_types or []),
            )
        except AggregatorClientError:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Failed to fetch KG snapshot for mission %s (namespace=%s)",
                mission.id,
                mission.kg_namespace,
                exc_info=True,
            )
            return None

        return snapshot if isinstance(snapshot, dict) else None

    def _fetch_kg_summary(self, mission: models.Mission) -> Dict[str, Any] | None:
        if not mission.kg_namespace:
            return None

        try:
            ensure_mission_namespace(mission, db=self.db)
            summary = self._aggregator.get_graph_summary(mission.kg_namespace)
        except AggregatorClientError:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Failed to fetch KG summary for mission %s (namespace=%s)",
                mission.id,
                mission.kg_namespace,
                exc_info=True,
            )
            return None

        return summary if isinstance(summary, dict) else None

    def _serialize_entities(self, mission_id: int) -> List[Dict[str, Any]]:
        entities = (
            self.db.query(models.Entity)
            .filter(models.Entity.mission_id == mission_id)
            .order_by(models.Entity.created_at.asc())
            .all()
        )
        return [
            {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "description": entity.description,
                "created_at": _isoformat_or_none(entity.created_at),
            }
            for entity in entities
        ]

    def _serialize_events(self, mission_id: int) -> List[Dict[str, Any]]:
        events = (
            self.db.query(models.Event)
            .filter(models.Event.mission_id == mission_id)
            .order_by(
                models.Event.timestamp.is_(None),
                models.Event.timestamp.asc(),
                models.Event.created_at.asc(),
            )
            .all()
        )
        return [
            {
                "id": event.id,
                "title": event.title,
                "summary": event.summary,
                "timestamp": _isoformat_or_none(event.timestamp),
                "location": event.location,
                "involved_entity_ids": list(event.involved_entity_ids or []),
            }
            for event in events
        ]

    def _serialize_datasets(self, mission_id: int) -> List[Dict[str, Any]]:
        datasets = (
            self.db.query(models.MissionDataset)
            .filter(models.MissionDataset.mission_id == mission_id)
            .order_by(models.MissionDataset.created_at.asc())
            .all()
        )
        return [
            {
                "id": dataset.id,
                "name": dataset.name,
                "status": dataset.status,
                "sources": dataset.sources,
                "profile": dataset.profile,
                "semantic_profile": dataset.semantic_profile,
                "created_at": _isoformat_or_none(dataset.created_at),
                "updated_at": _isoformat_or_none(dataset.updated_at),
            }
            for dataset in datasets
        ]


def _isoformat_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None
