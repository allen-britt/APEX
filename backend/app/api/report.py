from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.report_service import build_report_dataset
from app.db.session import get_db


router = APIRouter(tags=["reports"])


def _get_mission_or_404(mission_id: int, db: Session) -> models.Mission:
    mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


def _select_report_run(mission_id: int, db: Session, *, run_id: Optional[int]) -> Optional[models.AgentRun]:
    query = db.query(models.AgentRun).filter(models.AgentRun.mission_id == mission_id)

    if run_id is not None:
        run = query.filter(models.AgentRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Agent run not found for this mission")
        return run

    completed = (
        query.filter(models.AgentRun.status == "completed")
        .order_by(models.AgentRun.created_at.desc())
        .first()
    )
    if completed:
        return completed

    return query.order_by(models.AgentRun.created_at.desc()).first()


def _coerce_gaps(raw_gaps) -> Optional[List[str]]:
    if not raw_gaps:
        return None

    result: List[str] = []
    if isinstance(raw_gaps, list):
        for entry in raw_gaps:
            if isinstance(entry, dict):
                text = entry.get("description") or entry.get("summary") or ""
                if text:
                    result.append(text.strip())
                else:
                    result.append(str(entry).strip())
            else:
                result.append(str(entry).strip())
    elif isinstance(raw_gaps, str):
        lines = [line.strip() for line in raw_gaps.splitlines()]
        result.extend([line for line in lines if line])

    return [gap for gap in result if gap] or None


def _coerce_next_steps(raw_steps: Optional[str]) -> Optional[List[str]]:
    if not raw_steps:
        return None
    entries = [line.strip(" -*\t") for line in raw_steps.splitlines()]
    entries = [line for line in entries if line]
    return entries or None


@router.get(
    "/missions/{mission_id}/report",
    response_model=schemas.MissionReportResponse,
)
def get_mission_report(
    mission_id: int,
    run_id: Optional[int] = Query(default=None, ge=1),
    template: Optional[str] = Query(default=None, pattern="^(full|one_pager|delta)$"),
    as_dataset: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    mission = _get_mission_or_404(mission_id, db)

    documents = (
        db.query(models.Document)
        .filter(models.Document.mission_id == mission_id)
        .order_by(models.Document.created_at.desc())
        .all()
    )

    entities = (
        db.query(models.Entity)
        .filter(models.Entity.mission_id == mission_id)
        .order_by(models.Entity.created_at.desc())
        .all()
    )

    events = (
        db.query(models.Event)
        .filter(models.Event.mission_id == mission_id)
        .order_by(
            models.Event.timestamp.is_(None),
            models.Event.timestamp.asc(),
            models.Event.created_at.asc(),
        )
        .all()
    )

    run = _select_report_run(mission_id, db, run_id=run_id)

    guardrail = None
    gaps = None
    next_steps = None
    delta_summary = None

    if run:
        guardrail = schemas.GuardrailReport(
            overall_score=(run.guardrail_status or "").upper(),
            issues=run.guardrail_issues or [],
        )
        gaps = _coerce_gaps(getattr(run, "gaps", None))
        next_steps = _coerce_next_steps(run.next_steps)
        delta_summary = getattr(run, "delta_summary", None)

    response_payload = schemas.MissionReportResponse(
        mission=schemas.MissionResponse.from_orm(mission),
        documents=[schemas.DocumentResponse.from_orm(doc) for doc in documents],
        run=schemas.AgentRunResponse.from_orm(run) if run else None,
        entities=[schemas.EntityResponse.from_orm(entity) for entity in entities],
        events=[schemas.EventResponse.from_orm(event) for event in events],
        guardrail=guardrail,
        gaps=gaps,
        next_steps=next_steps,
        delta_summary=delta_summary,
        generated_at=datetime.now(timezone.utc),
    )

    if as_dataset or template:
        dataset = build_report_dataset(
            mission=mission,
            documents=documents,
            entities=entities,
            events=events,
            run=run,
            insights=None,
            guardrail=guardrail,
            generator_version="v0",
            model_name=None,
        )
        dataset.meta.template = template
        return JSONResponse(dataset.model_dump(mode="json"))

    return response_payload
