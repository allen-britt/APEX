from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app import models
from app.services.aggregator_client import AggregatorClient, AggregatorClientError


logger = logging.getLogger(__name__)

JOB_STATUS_PENDING = "PENDING"
JOB_STATUS_RUNNING = "RUNNING"
JOB_STATUS_SUCCESS = "SUCCESS"
JOB_STATUS_FAILED = "FAILED"


class MissionIngestJobService:
    def __init__(
        self,
        *,
        aggregator_client: Optional[AggregatorClient] = None,
        batch_size: int = 5,
    ) -> None:
        self._aggregator = aggregator_client or AggregatorClient()
        self._default_batch_size = max(1, batch_size)

    def enqueue_job(
        self,
        *,
        db: Session,
        mission: models.Mission,
        document: models.MissionDocument,
        text_content: str,
        metadata: Dict[str, Any],
    ) -> models.MissionIngestJob:
        job = models.MissionIngestJob(
            mission_id=mission.id,
            document_id=document.id,
            status=JOB_STATUS_PENDING,
            payload_text=text_content,
            metadata=metadata,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info(
            "mission_ingest_job_created",
            extra={
                "mission_id": mission.id,
                "document_id": document.id,
                "job_id": job.id,
            },
        )
        return job

    def list_jobs_for_mission(self, db: Session, mission_id: int) -> List[models.MissionIngestJob]:
        return (
            db.query(models.MissionIngestJob)
            .filter(models.MissionIngestJob.mission_id == mission_id)
            .order_by(models.MissionIngestJob.created_at.desc())
            .all()
        )

    def process_pending_jobs(
        self,
        db: Session,
        *,
        mission_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> int:
        batch_limit = limit or self._default_batch_size
        query = (
            db.query(models.MissionIngestJob)
            .options(
                joinedload(models.MissionIngestJob.document).joinedload(models.MissionDocument.mission)
            )
            .filter(models.MissionIngestJob.status == JOB_STATUS_PENDING)
            .order_by(models.MissionIngestJob.created_at.asc())
        )
        if mission_id is not None:
            query = query.filter(models.MissionIngestJob.mission_id == mission_id)

        jobs = query.limit(batch_limit).all()
        processed = 0
        for job in jobs:
            if self._process_job(db, job):
                processed += 1
        return processed

    def _process_job(self, db: Session, job: models.MissionIngestJob) -> bool:
        document = job.document
        mission = document.mission if document else None

        namespace = mission.kg_namespace if mission else None
        nodes_before: Optional[int] = None
        edges_before: Optional[int] = None
        if namespace:
            nodes_before, edges_before = self._graph_counts(namespace)

        job.status = JOB_STATUS_RUNNING
        job.attempts += 1
        job.last_error = None
        job.nodes_before = nodes_before
        job.edges_before = edges_before
        db.add(job)
        db.commit()
        db.refresh(job)

        if not mission or not namespace:
            error_msg = "Mission or KG namespace missing"
            self._mark_failure(db, job, document, error_msg)
            return False

        try:
            response = self._aggregator.ingest_document(
                namespace,
                title=(document.title or "Mission Document") if document else "Mission Document",
                text=job.payload_text or "",
                metadata=job.metadata_blob or {},
            )
        except AggregatorClientError as exc:  # pragma: no cover - network path
            self._mark_failure(db, job, document, str(exc))
            logger.error(
                "mission_ingest_job_failed",
                extra={
                    "mission_id": job.mission_id,
                    "document_id": job.document_id,
                    "job_id": job.id,
                    "error": str(exc),
                },
            )
            return False

        if document:
            document.aggregator_doc_id = response.get("id") if isinstance(response, dict) else None
            document.status = "INGESTED"
            db.add(document)

        nodes_after: Optional[int] = None
        edges_after: Optional[int] = None
        if namespace:
            nodes_after, edges_after = self._graph_counts(namespace)

        job.status = JOB_STATUS_SUCCESS
        job.last_error = None
        job.nodes_after = nodes_after
        job.edges_after = edges_after
        db.add(job)
        db.commit()
        logger.info(
            "mission_ingest_job_succeeded",
            extra={
                "mission_id": job.mission_id,
                "document_id": job.document_id,
                "job_id": job.id,
            },
        )
        return True

    def _mark_failure(
        self,
        db: Session,
        job: models.MissionIngestJob,
        document: Optional[models.MissionDocument],
        error_msg: str,
    ) -> None:
        job.status = JOB_STATUS_FAILED
        job.last_error = error_msg[:1000]
        if document:
            document.status = "FAILED"
            db.add(document)
        db.add(job)
        db.commit()

    def _graph_counts(self, namespace: str) -> tuple[Optional[int], Optional[int]]:
        try:
            summary = self._aggregator.get_graph_summary(namespace)
        except AggregatorClientError:
            logger.warning("graph_summary_failed", extra={"namespace": namespace})
            return None, None

        nodes = summary.get("nodes")
        edges = summary.get("edges")
        try:
            nodes_val = int(nodes) if nodes is not None else None
        except (TypeError, ValueError):  # pragma: no cover - defensive
            nodes_val = None
        try:
            edges_val = int(edges) if edges is not None else None
        except (TypeError, ValueError):  # pragma: no cover - defensive
            edges_val = None
        return nodes_val, edges_val
