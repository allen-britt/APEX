from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db


router = APIRouter(prefix="/missions", tags=["missions"])


@router.post("", response_model=schemas.MissionResponse, status_code=status.HTTP_201_CREATED)
def create_mission(
    mission_in: schemas.MissionCreate,
    db: Session = Depends(get_db),
) -> schemas.MissionResponse:
    mission = models.Mission(**mission_in.dict())
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


@router.get("", response_model=List[schemas.MissionResponse])
def list_missions(db: Session = Depends(get_db)) -> List[schemas.MissionResponse]:
    return db.query(models.Mission).order_by(models.Mission.created_at.desc()).all()


@router.get("/{mission_id}", response_model=schemas.MissionResponse)
def get_mission(
    mission_id: int,
    db: Session = Depends(get_db),
) -> schemas.MissionResponse:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission


@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mission(
    mission_id: int,
    db: Session = Depends(get_db),
) -> Response:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")

    db.delete(mission)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
