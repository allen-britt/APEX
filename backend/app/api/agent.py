from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.session import get_db
from app.services.agent_service import run_agent_cycle


router = APIRouter(tags=["agent_runs"])


def _get_mission_or_404(mission_id: int, db: Session) -> models.Mission:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission


@router.get("/missions/{mission_id}/agent_runs", response_model=List[schemas.AgentRunResponse])
def list_agent_runs(
    mission_id: int,
    db: Session = Depends(get_db),
) -> List[schemas.AgentRunResponse]:
    _get_mission_or_404(mission_id, db)
    return (
        db.query(models.AgentRun)
        .filter(models.AgentRun.mission_id == mission_id)
        .order_by(models.AgentRun.created_at.desc())
        .all()
    )


@router.post(
    "/missions/{mission_id}/analyze",
    response_model=schemas.AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_mission(
    mission_id: int,
    profile: str = Query("humint", regex="^(humint|sigint|osint)$"),
    db: Session = Depends(get_db),
) -> schemas.AgentRunResponse:
    _get_mission_or_404(mission_id, db)
    agent_run = await run_agent_cycle(mission_id, db, profile=profile)
    return agent_run


@router.delete("/agent_runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_run(run_id: int, db: Session = Depends(get_db)) -> None:
    """Hard-delete a single AgentRun by ID."""
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")

    db.delete(run)
    db.commit()


@router.delete(
    "/missions/{mission_id}/agent_runs",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_agent_runs_for_mission(
    mission_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Hard-delete all AgentRun records for a given mission."""
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")

    runs = (
        db.query(models.AgentRun)
        .filter(models.AgentRun.mission_id == mission_id)
        .all()
    )

    if not runs:
        return

    for run in runs:
        db.delete(run)

    db.commit()
