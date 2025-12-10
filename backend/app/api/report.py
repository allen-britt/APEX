from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.report_service import build_report_dataset
from app.services.report_template_engine import ReportTemplateEngine, TemplateNotFoundError
from app.services.template_filter import filter_templates_for_mission
from app.services.template_report_service import (
    TemplateGenerationError,
    TemplateReportService,
)
from app.services.gap_analysis_service import GapAnalysisService
from app.services.mission_context_service import MissionContextService
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



def get_template_engine() -> ReportTemplateEngine:
    return ReportTemplateEngine()


def get_gap_service(db: Session = Depends(get_db)) -> GapAnalysisService:
    return GapAnalysisService(db)


def get_template_report_service(db: Session = Depends(get_db)) -> TemplateReportService:
    return TemplateReportService(db)


@router.get("/reports/templates", response_model=List[schemas.ReportTemplateSummary])
def list_report_templates(
    mission_id: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    template_service: TemplateReportService = Depends(get_template_report_service),
):
    templates = template_service.list_templates()
    if mission_id is not None:
        mission = _get_mission_or_404(mission_id, db)
        templates = template_service.list_templates_for_mission(mission)
    return [
        schemas.ReportTemplateSummary(
            id=tpl.id,
            name=tpl.name,
            description=tpl.description,
            int_type=tpl.int_type,
            mission_domains=list(tpl.mission_domains),
            title10_allowed=tpl.title10_allowed,
            title50_allowed=tpl.title50_allowed,
            allowed_authorities=list(getattr(tpl, "allowed_authorities", []) or []),
            allowed_int_types=list(getattr(tpl, "allowed_int_types", []) or []),
            int_types=list(getattr(tpl, "int_types", []) or []),
            sections=[
                section
                if isinstance(section, str)
                else getattr(section, "title", str(section))
                for section in tpl.sections
            ],
        )
        for tpl in templates
    ]


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


@router.post(
    "/missions/{mission_id}/reports/from_template",
    response_model=schemas.TemplateReportGenerateResponse,
)
def generate_report_from_template(
    mission_id: int,
    payload: schemas.TemplateReportGenerateRequest,
    service: TemplateReportService = Depends(get_template_report_service),
):
    try:
        result = service.generate_report(mission_id, payload.template_id)
    except TemplateGenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result


@router.post(
    "/missions/{mission_id}/reports",
    response_model=schemas.ReportTemplateResponse,
)
async def generate_templated_report(
    mission_id: int,
    template: str = Query(..., min_length=1),
    persist: bool = Query(default=False),
    db: Session = Depends(get_db),
    engine: ReportTemplateEngine = Depends(get_template_engine),
    gap_service: GapAnalysisService = Depends(get_gap_service),
):
    mission = _get_mission_or_404(mission_id, db)

    gap_data = mission.gap_analysis if isinstance(mission.gap_analysis, dict) else None
    if not gap_data:
        gap_result = await gap_service.run_gap_analysis(mission_id)
        gap_data = gap_result.model_dump(mode="json")
        mission.gap_analysis = gap_data
        db.add(mission)
        db.commit()
        db.refresh(mission)

    context_service = MissionContextService(db)
    mission_context = context_service.build_context_for_mission(mission)
    if gap_data:
        mission_context["gap_analysis"] = gap_data

    try:
        rendered = await engine.render_template(
            template_id=template,
            context=mission_context,
        )
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    allowed_templates = filter_templates_for_mission(
        mission=mission,
        templates=engine.get_all_templates(),
    )
    if not any(tpl.id == template for tpl in allowed_templates):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Template is not authorized for this mission's authority",
        )

    if persist:
        record = _persist_template_report(mission, rendered, db)
        if record:
            metadata = rendered.setdefault("metadata", {})
            metadata["record_id"] = record["id"]
            metadata["stored_at"] = record["stored_at"]

    return schemas.ReportTemplateResponse(**rendered)


@router.get(
    "/missions/{mission_id}/reports/templates",
    response_model=List[schemas.TemplateReportRecord],
)
def list_saved_template_reports(
    mission_id: int,
    db: Session = Depends(get_db),
):
    mission = _get_mission_or_404(mission_id, db)
    reports = mission.template_reports if isinstance(mission.template_reports, list) else []
    return reports


def _persist_template_report(
    mission: models.Mission,
    rendered: Dict[str, Any],
    db: Session,
    *,
    max_records: int = 10,
) -> Optional[Dict[str, Any]]:
    sections = rendered.get("sections")
    if not isinstance(sections, list):
        return None

    stored_at = datetime.now(timezone.utc).isoformat()
    record = {
        "id": str(uuid4()),
        "template_id": rendered.get("template_id"),
        "template_name": rendered.get("template_name"),
        "sections": sections,
        "metadata": rendered.get("metadata", {}),
        "stored_at": stored_at,
    }

    existing = mission.template_reports if isinstance(mission.template_reports, list) else []
    mission.template_reports = [record, *existing][:max_records]
    mission.updated_at = datetime.now(timezone.utc)
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return record
