"""Mission dataset API routes."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db
from app.services.dataset_builder_service import (
    DatasetBuilderService,
    DatasetBuilderServiceError,
)
from app.services.semantic_profiler import (
    SemanticProfiler,
    SemanticProfilerError,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/missions/{mission_id}/datasets", tags=["mission_datasets"])


def get_builder_service() -> DatasetBuilderService:
    return DatasetBuilderService()


def get_semantic_profiler() -> SemanticProfiler:
    return SemanticProfiler()


def _get_mission_or_404(mission_id: int, db: Session) -> models.Mission:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission


def _get_dataset_or_404(mission_id: int, dataset_id: int, db: Session) -> models.MissionDataset:
    dataset = (
        db.query(models.MissionDataset)
        .filter(models.MissionDataset.id == dataset_id, models.MissionDataset.mission_id == mission_id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@router.post("", response_model=schemas.MissionDatasetRead, status_code=status.HTTP_201_CREATED)
def create_dataset(
    mission_id: int,
    payload: schemas.MissionDatasetCreate,
    db: Session = Depends(get_db),
    builder: DatasetBuilderService = Depends(get_builder_service),
) -> schemas.MissionDatasetRead:
    _get_mission_or_404(mission_id, db)

    try:
        profile = builder.build_dataset_profile(payload.sources)
    except DatasetBuilderServiceError as exc:
        logger.exception("Failed to build mission dataset profile")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to build mission dataset profile",
        ) from exc

    dataset = models.MissionDataset(
        mission_id=mission_id,
        name=payload.name,
        status="ready",
        sources=payload.sources,
        profile=profile,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("", response_model=List[schemas.MissionDatasetRead])
def list_datasets(mission_id: int, db: Session = Depends(get_db)) -> List[schemas.MissionDatasetRead]:
    _get_mission_or_404(mission_id, db)
    return (
        db.query(models.MissionDataset)
        .filter(models.MissionDataset.mission_id == mission_id)
        .order_by(models.MissionDataset.created_at.desc())
        .all()
    )


@router.get("/{dataset_id}", response_model=schemas.MissionDatasetRead)
def get_dataset(
    mission_id: int,
    dataset_id: int,
    db: Session = Depends(get_db),
) -> schemas.MissionDatasetRead:
    _get_mission_or_404(mission_id, db)
    return _get_dataset_or_404(mission_id, dataset_id, db)


@router.post(
    "/{dataset_id}/semantic_profile",
    response_model=schemas.MissionDatasetRead,
    status_code=status.HTTP_200_OK,
)
def build_semantic_profile(
    mission_id: int,
    dataset_id: int,
    db: Session = Depends(get_db),
    profiler: SemanticProfiler = Depends(get_semantic_profiler),
) -> schemas.MissionDatasetRead:
    _get_mission_or_404(mission_id, db)
    dataset = _get_dataset_or_404(mission_id, dataset_id, db)

    if not dataset.profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset must have a profile before semantic profiling",
        )

    try:
        semantic_profile = profiler.generate(dataset)
    except SemanticProfilerError as exc:
        logger.exception("Failed to generate semantic profile for dataset %s", dataset_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate semantic profile",
        ) from exc

    dataset.semantic_profile = semantic_profile
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset
