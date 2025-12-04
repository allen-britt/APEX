from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models
from app.services.ingest_job_service import MissionIngestJobService

logger = logging.getLogger(__name__)


@dataclass
class MissionDocumentPayload:
    mission: models.Mission
    source_type: str
    title: Optional[str]
    primary_int: Optional[str]
    int_types: List[str]
    text_content: str
    storage_path: Optional[str] = None


class MissionDocumentServiceError(Exception):
    """Raised when mission document ingestion fails."""


class MissionDocumentService:
    def __init__(
        self,
        *,
        storage_dir: Path,
        ingest_job_service: Optional[MissionIngestJobService] = None,
    ) -> None:
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._jobs = ingest_job_service or MissionIngestJobService()

    def ingest_file(
        self,
        *,
        db: Session,
        mission: models.Mission,
        filename: str,
        data: bytes,
        primary_int: Optional[str],
        int_types: List[str],
    ) -> models.MissionDocument:
        if not filename:
            filename = "mission-upload.bin"
        storage_path = self._persist_file(mission.id, filename, data)
        text_content = self._bytes_to_text(data)
        payload = MissionDocumentPayload(
            mission=mission,
            source_type="file",
            title=filename,
            primary_int=primary_int,
            int_types=int_types,
            text_content=text_content,
            storage_path=str(storage_path),
        )
        return self._ingest(db=db, payload=payload)

    def ingest_text(
        self,
        *,
        db: Session,
        mission: models.Mission,
        source_type: str,
        title: Optional[str],
        primary_int: Optional[str],
        int_types: List[str],
        text_content: str,
    ) -> models.MissionDocument:
        payload = MissionDocumentPayload(
            mission=mission,
            source_type=source_type,
            title=title,
            primary_int=primary_int,
            int_types=int_types,
            text_content=text_content or "",
        )
        return self._ingest(db=db, payload=payload)

    def _persist_file(self, mission_id: int, filename: str, data: bytes) -> Path:
        mission_dir = self._storage_dir / f"mission_{mission_id}"
        mission_dir.mkdir(parents=True, exist_ok=True)
        target_path = mission_dir / filename
        with target_path.open("wb") as buffer:
            buffer.write(data)
        return target_path

    @staticmethod
    def _bytes_to_text(data: bytes) -> str:
        if not data:
            return ""
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="ignore")

    def _ingest(self, *, db: Session, payload: MissionDocumentPayload) -> models.MissionDocument:
        if not payload.mission.kg_namespace:
            raise MissionDocumentServiceError("Mission does not have a KG namespace")

        doc = models.MissionDocument(
            mission_id=payload.mission.id,
            source_type=payload.source_type,
            title=payload.title,
            original_path=payload.storage_path,
            primary_int=payload.primary_int,
            int_types=payload.int_types,
            status="PENDING",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        metadata = {
            "mission_id": payload.mission.id,
            "mission_name": payload.mission.name,
            "primary_authority": payload.mission.primary_authority,
            "int_types": payload.int_types,
            "primary_int": payload.primary_int,
            "source_type": payload.source_type,
        }

        job = self._jobs.enqueue_job(
            db=db,
            mission=payload.mission,
            document=doc,
            text_content=payload.text_content or "",
            metadata=metadata,
        )
        logger.info(
            "mission_document_enqueued",
            extra={
                "mission_id": payload.mission.id,
                "document_id": doc.id,
                "job_id": job.id,
                "source_type": payload.source_type,
            },
        )
        db.refresh(doc)

        return doc
