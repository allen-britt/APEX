from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db
from app.services.kg_client import KgClient, KgClientError
from app.services.namespace_service import ensure_mission_namespace


router = APIRouter(tags=["graph"])
_kg_client = KgClient()


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


def _require_project_id(mission: models.Mission) -> str:
    if mission.kg_namespace:
        return mission.kg_namespace
    # Fall back to the KgClient naming convention if namespace isn't persisted yet
    return KgClient.project_id_from_mission(mission.id)


@router.get("/missions/{mission_id}/kg/summary")
def get_mission_kg_summary(
    mission_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    mission = _ensure_mission(mission_id, db)
    project_id = ensure_mission_namespace(mission, db=db)
    try:
        return _kg_client.get_summary(project_id)
    except KgClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch mission KG summary",
        ) from exc


@router.get("/missions/{mission_id}/kg/full")
def get_mission_full_graph(
    mission_id: int,
    limit_nodes: int = 400,
    limit_edges: int = 800,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    mission = _ensure_mission(mission_id, db)
    project_id = ensure_mission_namespace(mission, db=db)
    try:
        return _kg_client.get_full_graph(
            project_id,
            limit_nodes=limit_nodes,
            limit_edges=limit_edges,
        )
    except KgClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch mission KG graph",
        ) from exc


@router.get("/missions/{mission_id}/kg/neighborhood")
def get_mission_kg_neighborhood(
    mission_id: int,
    node_id: str,
    hops: int = 2,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    mission = _ensure_mission(mission_id, db)
    if not node_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="node_id is required")

    project_id = ensure_mission_namespace(mission, db=db)
    try:
        return _kg_client.get_neighborhood(project_id, node_id, hops=hops)
    except KgClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch KG neighborhood",
        ) from exc


@router.get("/missions/{mission_id}/kg/suggest-links")
def get_mission_kg_suggested_links(
    mission_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    mission = _ensure_mission(mission_id, db)
    project_id = ensure_mission_namespace(mission, db=db)
    try:
        return _kg_client.get_suggested_links(project_id, limit=limit)
    except KgClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch KG link suggestions",
        ) from exc
