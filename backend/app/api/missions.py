import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db
from app.policy_authorities import (
    authority_id_to_label,
    authority_id_to_legacy_key,
    get_pivot_rule,
    normalize_authority_id,
)
from app.services.aggregator_client import AggregatorClient, AggregatorClientError
from app.services.namespace_service import ensure_mission_namespace
from app.services.policy_context import find_disallowed_ints


router = APIRouter(prefix="/missions", tags=["missions"])
logger = logging.getLogger(__name__)
_aggregator_client = AggregatorClient()


def _mission_with_latest_run(mission: models.Mission, db: Session) -> schemas.MissionResponse:
    response = schemas.MissionResponse.from_orm(mission)
    latest_run = (
        db.query(models.AgentRun)
        .filter(models.AgentRun.mission_id == mission.id)
        .order_by(models.AgentRun.created_at.desc())
        .first()
    )
    if latest_run:
        response.latest_agent_run = schemas.AgentRunResponse.from_orm(latest_run)
    return response


@router.post("", response_model=schemas.MissionResponse, status_code=status.HTTP_201_CREATED)
def create_mission(
    mission_in: schemas.MissionCreate,
    db: Session = Depends(get_db),
) -> schemas.MissionResponse:
    mission = models.Mission(**mission_in.dict())
    # Ensure original authority is locked to the first assigned value
    mission.original_authority = mission.primary_authority
    warnings = find_disallowed_ints(mission.primary_authority, mission.int_types)
    if warnings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Mission INT selection exceeds authority lane", "issues": warnings},
        )
    db.add(mission)
    db.commit()
    db.refresh(mission)

    ensure_mission_namespace(mission, db=db)

    return _mission_with_latest_run(mission, db)


@router.put("/{mission_id}", response_model=schemas.MissionResponse)
def update_mission(
    mission_id: int,
    mission_in: schemas.MissionCreate,
    db: Session = Depends(get_db),
) -> schemas.MissionResponse:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")

    for field, value in mission_in.dict().items():
        if field == "original_authority":
            continue
        setattr(mission, field, value)

    warnings = find_disallowed_ints(mission.primary_authority, mission.int_types)
    if warnings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Mission INT selection exceeds authority lane", "issues": warnings},
        )

    db.add(mission)
    db.commit()
    db.refresh(mission)
    return _mission_with_latest_run(mission, db)


@router.post("/{mission_id}/pivot-authority", response_model=schemas.MissionResponse)
def pivot_mission_authority(
    mission_id: int,
    payload: schemas.MissionAuthorityPivotRequest,
    db: Session = Depends(get_db),
) -> schemas.MissionResponse:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")

    current_authority = normalize_authority_id(mission.primary_authority)
    if not current_authority:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mission authority is not recognized")

    target_authority = normalize_authority_id(payload.target_authority)
    if not target_authority:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target authority is not recognized")

    if target_authority == current_authority:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mission is already under this authority",
        )

    rule = get_pivot_rule(current_authority, target_authority)
    if not rule or not rule["allowed"]:
        detail = {
            "message": "Pivot from {0} to {1} is not permitted under policy".format(
                authority_id_to_label(current_authority), authority_id_to_label(target_authority)
            ),
            "conditions": rule["conditions"] if rule else [],
        }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    justification = (payload.justification or "").strip()
    if len(justification) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Justification must be at least 10 characters",
        )

    new_authority_value = authority_id_to_legacy_key(target_authority)

    pivot_record = models.MissionAuthorityPivot(
        mission_id=mission.id,
        from_authority=mission.primary_authority,
        to_authority=new_authority_value,
        justification=justification,
        risk=rule["risk"],
        allowed=True,
        conditions=rule["conditions"],
        actor="system",
    )

    mission.primary_authority = new_authority_value
    db.add(pivot_record)
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return _mission_with_latest_run(mission, db)


@router.get("", response_model=List[schemas.MissionResponse])
def list_missions(db: Session = Depends(get_db)) -> List[schemas.MissionResponse]:
    missions = db.query(models.Mission).order_by(models.Mission.created_at.desc()).all()
    return [_mission_with_latest_run(mission, db) for mission in missions]


@router.get("/{mission_id}", response_model=schemas.MissionResponse)
def get_mission(
    mission_id: int,
    db: Session = Depends(get_db),
) -> schemas.MissionResponse:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return _mission_with_latest_run(mission, db)


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
