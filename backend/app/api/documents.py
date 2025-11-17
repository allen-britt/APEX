from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db


router = APIRouter(tags=["documents"])


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
