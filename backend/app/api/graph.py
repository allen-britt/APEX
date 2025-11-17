from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db


router = APIRouter(tags=["graph"])


def _ensure_mission(mission_id: int, db: Session) -> models.Mission:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission


def _get_entity_or_404(entity_id: int, db: Session) -> models.Entity:
    entity = db.query(models.Entity).filter(models.Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity


def _get_event_or_404(event_id: int, db: Session) -> models.Event:
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.get("/missions/{mission_id}/graph", response_model=Dict[str, List])
def get_graph(
    mission_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, List]:
    _ensure_mission(mission_id, db)
    entities = (
        db.query(models.Entity)
        .filter(models.Entity.mission_id == mission_id)
        .order_by(models.Entity.created_at.desc())
        .all()
    )
    events = (
        db.query(models.Event)
        .filter(models.Event.mission_id == mission_id)
        .order_by(models.Event.created_at.desc())
        .all()
    )
    return {
        "entities": [schemas.EntityResponse.from_orm(entity) for entity in entities],
        "events": [schemas.EventResponse.from_orm(event) for event in events],
    }


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity_id: int, db: Session = Depends(get_db)) -> None:
    entity = _get_entity_or_404(entity_id, db)
    db.delete(entity)
    db.commit()


@router.delete("/missions/{mission_id}/entities", status_code=status.HTTP_204_NO_CONTENT)
def delete_entities_for_mission(mission_id: int, db: Session = Depends(get_db)) -> None:
    _ensure_mission(mission_id, db)
    entities = (
        db.query(models.Entity)
        .filter(models.Entity.mission_id == mission_id)
        .all()
    )
    if not entities:
        return

    for entity in entities:
        db.delete(entity)

    db.commit()


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db)) -> None:
    event = _get_event_or_404(event_id, db)
    db.delete(event)
    db.commit()


@router.delete("/missions/{mission_id}/events", status_code=status.HTTP_204_NO_CONTENT)
def delete_events_for_mission(mission_id: int, db: Session = Depends(get_db)) -> None:
    _ensure_mission(mission_id, db)
    events = (
        db.query(models.Event)
        .filter(models.Event.mission_id == mission_id)
        .all()
    )
    if not events:
        return

    for event in events:
        db.delete(event)

    db.commit()
