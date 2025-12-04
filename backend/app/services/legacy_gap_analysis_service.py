from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from app.services import llm_client
from app.services.kg_client import KgClient, KgClientError

logger = logging.getLogger(__name__)


class GapAnalysisError(Exception):
    """Raised when gap analysis cannot be produced."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LegacyGapAnalysisService:
    """Original gap analysis implementation backed by AggreGator."""

    def __init__(
        self,
        *,
        kg_client: Optional[KgClient] = None,
        enable_llm_fallback: bool = True,
    ) -> None:
        self._kg = kg_client or KgClient()
        self._enable_llm = enable_llm_fallback

    def _fetch_kg_summary(self, mission_id: int) -> Optional[Dict[str, Any]]:
        project_id = self._kg.project_id_from_mission(mission_id)
        try:
            return self._kg.get_summary(project_id)
        except KgClientError:
            logger.warning("KG summary unavailable for mission %s", mission_id, exc_info=True)
            return None

    def _build_missing_data(self, graph_summary: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not graph_summary:
            return [
                {
                    "title": "No KG summary",
                    "detail": "AggreGator graph summary unavailable; ensure project ingestion.",
                    "severity": "high",
                }
            ]

        top_labels = graph_summary.get("top_labels") or []
        if not top_labels:
            return [
                {
                    "title": "Empty knowledge graph",
                    "detail": "AggreGator reported no labeled nodes",
                    "severity": "high",
                }
            ]

        label_names = {entry.get("label", "").upper() for entry in top_labels if isinstance(entry, dict)}
        expected = {"PERSON", "FACILITY", "EVENT"}
        missing = sorted(expected - label_names)
        if not missing:
            return []
        return [
            {
                "title": "Missing node categories",
                "detail": f"Graph lacks {', '.join(missing)} nodes",
                "severity": "medium",
                "metadata": {"missing_labels": missing},
            }
        ]

    def _quality_findings(self, datasets: List[models.MissionDataset]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for dataset in datasets:
            profile = dataset.profile or {}
            tables = profile.get("tables") if isinstance(profile, dict) else None
            if not tables:
                findings.append(
                    {
                        "title": f"Dataset {dataset.name} lacks profile",
                        "detail": "AggreGator profile missing or malformed",
                        "severity": "medium",
                        "metadata": {"dataset_id": dataset.id},
                    }
                )
                continue
            for table in tables:
                if not isinstance(table, dict):
                    continue
                columns = table.get("columns")
                if not isinstance(columns, list):
                    continue
                null_heavy = [
                    col.get("name")
                    for col in columns
                    if isinstance(col, dict) and (col.get("null_fraction") or 0) >= 0.3
                ]
                if null_heavy:
                    findings.append(
                        {
                            "title": f"Null-heavy columns in {table.get('name', 'table')}",
                            "detail": f"Columns {', '.join(null_heavy)} exceed 30% nulls",
                            "severity": "medium",
                            "metadata": {"dataset_id": dataset.id, "table": table.get("name")},
                        }
                    )
        return findings

    async def _llm_conflicts(
        self,
        mission: models.Mission,
        entities: List[models.Entity],
        events: List[models.Event],
    ) -> List[Dict[str, Any]]:
        if not self._enable_llm:
            return []
        entity_dicts = [{"name": e.name, "type": e.type, "description": e.description} for e in entities]
        event_dicts = [
            {
                "title": ev.title,
                "summary": ev.summary,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "location": ev.location,
            }
            for ev in events
        ]
        try:
            result = await llm_client.detect_information_gaps([], entity_dicts, event_dicts)
        except Exception:
            logger.exception("LLM gap detection failed")
            return []
        gaps = result.get("gaps") if isinstance(result, dict) else None
        if not isinstance(gaps, list):
            return []
        conflicts: List[Dict[str, Any]] = []
        for gap in gaps:
            if not isinstance(gap, dict):
                continue
            conflicts.append(
                {
                    "title": gap.get("description", "Gap"),
                    "detail": gap.get("description"),
                    "severity": gap.get("priority", "medium"),
                }
            )
        return conflicts

    async def analyze(self, mission_id: int, db: Session) -> Dict[str, Any]:
        logger.info("legacy_gap_analysis.start", extra={"mission_id": mission_id})
        mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
        if not mission:
            logger.warning("legacy_gap_analysis.mission_missing", extra={"mission_id": mission_id})
            raise GapAnalysisError("Mission not found")

        datasets = (
            db.query(models.MissionDataset)
            .filter(models.MissionDataset.mission_id == mission_id)
            .order_by(models.MissionDataset.created_at.desc())
            .all()
        )
        entities = (
            db.query(models.Entity)
            .filter(models.Entity.mission_id == mission_id)
            .order_by(models.Entity.created_at.desc())
            .all()
        )
        events = (
            db.query(models.Event)
            .filter(models.Event.mission_id == mission_id)
            .order_by(models.Event.timestamp.is_(None), models.Event.timestamp.asc())
            .all()
        )

        logger.info(
            "legacy_gap_analysis.inputs",
            extra={
                "mission_id": mission_id,
                "dataset_count": len(datasets),
                "entity_count": len(entities),
                "event_count": len(events),
            },
        )

        kg_summary = self._fetch_kg_summary(mission_id)
        if kg_summary is None:
            logger.warning("legacy_gap_analysis.kg_summary_missing", extra={"mission_id": mission_id})
        missing_data = self._build_missing_data(kg_summary)
        quality_findings = self._quality_findings(datasets)

        time_gaps: List[Dict[str, Any]] = []
        dated = [event.timestamp for event in events if event.timestamp]
        if len(dated) >= 2:
            dated.sort()
            spans = [
                (dated[i + 1] - dated[i]).days
                for i in range(len(dated) - 1)
                if dated[i] and dated[i + 1]
            ]
            if spans and max(spans) > 3:
                time_gaps.append(
                    {
                        "title": "Timeline gap",
                        "detail": f"Detected {max(spans)} day gap between known events",
                        "severity": "medium",
                    }
                )

        high_value_unknowns: List[Dict[str, Any]] = []
        if datasets and entities:
            high_value_unknowns.append(
                {
                    "title": "Corroboration needed",
                    "detail": "Key entities lack cross-dataset validation",
                    "severity": "medium",
                }
            )

        priorities = {
            "entities": [
                {
                    "name": entity.name or "Unnamed",
                    "reason": entity.description or "High connectivity",
                    "type": entity.type,
                    "reference_id": entity.id,
                }
                for entity in entities[:5]
            ],
            "events": [
                {
                    "name": event.title,
                    "reason": event.summary or "Key timeline event",
                    "reference_id": event.id,
                }
                for event in events[:5]
            ],
            "rationale": "Based on KG coverage and mission timeline",
        }

        conflicts = await self._llm_conflicts(mission, entities, events)

        result = {
            "generated_at": _now(),
            "kg_summary": kg_summary,
            "missing_data": missing_data,
            "time_gaps": time_gaps,
            "conflicts": conflicts,
            "high_value_unknowns": high_value_unknowns,
            "quality_findings": quality_findings,
            "priorities": priorities,
        }
        logger.info(
            "legacy_gap_analysis.complete",
            extra={
                "mission_id": mission_id,
                "missing_findings": len(missing_data),
                "quality_findings": len(quality_findings),
                "conflict_findings": len(conflicts),
            },
        )
        return result
