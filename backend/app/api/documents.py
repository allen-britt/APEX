from pathlib import Path
from typing import Annotated, List, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import SessionLocal, get_db
from app.config_documents import get_mission_documents_storage_dir
from app.services.ingest_job_service import MissionIngestJobService
from app.services.mission_document_service import (
    MissionDocumentService,
    MissionDocumentServiceError,
)


router = APIRouter(tags=["documents"])
_ingest_job_service = MissionIngestJobService()
_mission_doc_service = MissionDocumentService(
    storage_dir=get_mission_documents_storage_dir(),
    ingest_job_service=_ingest_job_service,
)


def _drain_ingest_jobs(mission_id: Optional[int] = None) -> None:
    db = SessionLocal()
    try:
        processed = _ingest_job_service.process_pending_jobs(db, mission_id=mission_id)
        if processed:
            # logger import is optional; rely on router logger if desired
            pass
    finally:
        db.close()


def _schedule_ingest_drain(background_tasks: BackgroundTasks, mission_id: Optional[int]) -> None:
    background_tasks.add_task(_drain_ingest_jobs, mission_id)


def _get_mission_or_404(mission_id: int, db: Session) -> models.Mission:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission


def _get_document_or_404(document_id: int, db: Session) -> models.Document:
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _get_mission_document_or_404(document_id: str, db: Session) -> models.MissionDocument:
    document = db.query(models.MissionDocument).filter(models.MissionDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission document not found")
    return document


@router.post(
    "/missions/{mission_id}/documents",
    response_model=schemas.DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    mission_id: int,
    document_in: schemas.DocumentCreate,
    db: Session = Depends(get_db),
) -> schemas.DocumentResponse:
    _get_mission_or_404(mission_id, db)
    document = models.Document(mission_id=mission_id, **document_in.model_dump())
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post(
    "/missions/{mission_id}/documents/upload",
    response_model=schemas.MissionDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_mission_document(
    mission_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    primary_int: str | None = Form(None),
    int_types: Annotated[List[str] | None, Form()] = None,
    db: Session = Depends(get_db),
):
    mission = _get_mission_or_404(mission_id, db)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    int_types = int_types or []

    try:
        document = _mission_doc_service.ingest_file(
            db=db,
            mission=mission,
            filename=title or file.filename,
            data=data,
            primary_int=primary_int,
            int_types=int_types,
        )
    except MissionDocumentServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _schedule_ingest_drain(background_tasks, mission_id)
    return document


@router.post(
    "/missions/{mission_id}/documents/url",
    response_model=schemas.MissionDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_mission_document_url(
    mission_id: int,
    payload: schemas.MissionDocumentUrlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    mission = _get_mission_or_404(mission_id, db)
    try:
        response = httpx.get(str(payload.url), timeout=15)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch URL") from exc

    text = response.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fetched URL contains no text")

    try:
        document = _mission_doc_service.ingest_text(
            db=db,
            mission=mission,
            source_type="url",
            title=payload.title or str(payload.url),
            primary_int=payload.primary_int,
            int_types=payload.int_types,
            text_content=text,
        )
    except MissionDocumentServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _schedule_ingest_drain(background_tasks, mission_id)
    return document


@router.get(
    "/missions/{mission_id}/mission-documents",
    response_model=List[schemas.MissionDocumentResponse],
)
def list_mission_documents(
    mission_id: int,
    db: Session = Depends(get_db),
):
    _get_mission_or_404(mission_id, db)
    return (
        db.query(models.MissionDocument)
        .filter(models.MissionDocument.mission_id == mission_id)
        .order_by(models.MissionDocument.created_at.desc())
        .all()
    )


@router.delete(
    "/missions/{mission_id}/mission-documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_mission_document(
    mission_id: int,
    document_id: str,
    db: Session = Depends(get_db),
) -> Response:
    mission = _get_mission_or_404(mission_id, db)
    document = _get_mission_document_or_404(document_id, db)
    if document.mission_id != mission.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission document not found")

    original_path = document.original_path
    db.delete(document)
    db.commit()

    if original_path:
        try:
            path = Path(original_path)
            path.unlink(missing_ok=True)
        except Exception:  # pragma: no cover - best-effort cleanup
            pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/missions/{mission_id}/ingest-jobs",
    response_model=List[schemas.MissionIngestJobResponse],
)
def list_mission_ingest_jobs(
    mission_id: int,
    db: Session = Depends(get_db),
):
    _get_mission_or_404(mission_id, db)
    return _ingest_job_service.list_jobs_for_mission(db, mission_id)


@router.post(
    "/missions/{mission_id}/ingest-jobs/drain",
    response_model=schemas.MissionIngestJobDrainResponse,
)
def drain_mission_ingest_jobs(
    mission_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    mission = _get_mission_or_404(mission_id, db)
    _schedule_ingest_drain(background_tasks, mission.id)
    return schemas.MissionIngestJobDrainResponse(mission_id=mission.id)


@router.get(
    "/missions/{mission_id}/documents",
    response_model=List[schemas.DocumentResponse],
)
def list_documents(
    mission_id: int,
    db: Session = Depends(get_db),
) -> List[schemas.DocumentResponse]:
    _get_mission_or_404(mission_id, db)
    return (
        db.query(models.Document)
        .filter(models.Document.mission_id == mission_id)
        .order_by(models.Document.created_at.desc())
        .all()
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> Response:
    document = _get_document_or_404(document_id, db)
    db.delete(document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/documents/{document_id}", response_model=schemas.DocumentResponse)
def update_document(
    document_id: int,
    payload: schemas.DocumentUpdate,
    db: Session = Depends(get_db),
) -> schemas.DocumentResponse:
    document = _get_document_or_404(document_id, db)

    if payload.mission_id is not None and payload.mission_id != document.mission_id:
        _get_mission_or_404(payload.mission_id, db)
        document.mission_id = payload.mission_id

    if payload.include_in_analysis is not None:
        document.include_in_analysis = payload.include_in_analysis

    db.commit()
    db.refresh(document)
    return document
