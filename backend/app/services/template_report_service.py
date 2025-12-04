from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app import models
from app.models.decision_dataset import DecisionDataset
from app.models.evidence import EvidenceBundle
from app.services.decision_dataset_service import DecisionDatasetService
from app.services.evidence_extractor_service import EvidenceExtractorService
from app.services.llm_client import LLMClient, LlmError
from app.services.kg_snapshot_utils import summarize_kg_snapshot
from app.services.mission_context_service import MissionContextError, MissionContextService
from app.services.prompt_builder import build_global_system_prompt
from app.services.template_filter import filter_templates_for_mission
from app.services.template_service import (
    InternalReportTemplate,
    TemplateDefinitionNotFound,
    TemplateService,
)
import markdown2
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


_PLACEHOLDER_PATTERN = re.compile(r"\{\{[^{}]+\}\}")
_REPORT_META_PATTERNS = [
    r"agent run advisory",
    r"agent run",
    r"agent analysis",
    r"mission text",
    r"provided context",
    r"provided json",
    r"provided entities",
    r"provided events",
    r"event id\s*\d+",
    r"evidence\.[a-zA-Z0-9_]+\[[0-9]+\]",
    r"evidence\s*:\s*incidents\[[0-9]+\]",
    r"evidence\s*:\s*evidence\[[0-9]+\]",
    r"provide\s+(high|medium|low)",
    r"json",
    r"context",
]
_CAPITALIZED_TOKEN_PATTERN = re.compile(r"\b([A-Z][A-Za-z]+)\b")
_DATE_TOKEN_PATTERN = re.compile(r"\b(\d{4}(?:-\d{2}-\d{2})?)\b")
_BASE_ALLOWED_TERMS = {
    "leo",
    "mission",
    "authority",
    "int",
    "lanes",
    "prepared",
    "date",
    "key",
    "judgments",
    "incident",
    "overview",
    "patterns",
    "subjects",
    "associates",
    "modus",
    "operandi",
    "evidence",
    "corroboration",
    "gaps",
    "constraints",
    "recommended",
    "actions",
    "risk",
    "civil",
    "liberties",
    "considerations",
    "none",
    "available",
    "based",
    "current",
    "evidence",
}
_TEMPLATE_FILL_RULES = (
    "- Replace every placeholder like {{placeholder}} or {{array[index].field}} with actual prose or a clear 'Not available'.\n"
    "- Never emit literal '{{' or '}}' in the final report.\n"
    "- Keep the provided section order and headings exactly as shown."
)


def _strip_placeholders(text: str) -> str:
    if not text:
        return ""
    return _PLACEHOLDER_PATTERN.sub("Not available", text)


def _clean_markdown_output(raw_markdown: str) -> str:
    cleaned = (raw_markdown or "").strip()
    return _strip_placeholders(cleaned)


def _sanitize_report_markdown(markdown_text: str | None) -> str:
    text = (markdown_text or "").strip()
    if not text:
        return ""
    for pattern in _REPORT_META_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _collect_allowed_terms(bundle: EvidenceBundle) -> set[str]:
    allowed: set[str] = set(_BASE_ALLOWED_TERMS)

    def _add_term(value: str | None) -> None:
        if not value:
            return
        term = str(value).strip()
        if not term:
            return
        lower = term.lower()
        allowed.add(lower)
        for token in re.findall(r"[A-Za-z0-9/-]+", term):
            allowed.add(token.lower())

    if not bundle:
        return allowed

    _add_term(bundle.mission_name)
    _add_term(bundle.authority)
    for lane in getattr(bundle, "int_lanes", []) or []:
        _add_term(lane)

    for incident in getattr(bundle, "incidents", []) or []:
        _add_term(getattr(incident, "summary", None))
        _add_term(getattr(incident, "location", None))
        _add_term(getattr(incident, "occurred_at", None))

    for subject in getattr(bundle, "subjects", []) or []:
        _add_term(getattr(subject, "name", None))
        _add_term(getattr(subject, "description", None))
        _add_term(getattr(subject, "type", None))

    for associate in getattr(bundle, "associates", []) or []:
        _add_term(getattr(associate, "name", None))
        _add_term(getattr(associate, "description", None))

    for location in getattr(bundle, "locations", []) or []:
        _add_term(getattr(location, "name", None))
        _add_term(getattr(location, "description", None))

    for event in getattr(bundle, "events", []) or []:
        _add_term(getattr(event, "description", None))
        _add_term(getattr(event, "occurred_at", None))

    for document in getattr(bundle, "documents", []) or []:
        _add_term(getattr(document, "title", None))

    for gap in getattr(bundle, "gaps", []) or []:
        _add_term(getattr(gap, "description", None))

    if getattr(bundle, "kg_snapshot_summary", None):
        _add_term(bundle.kg_snapshot_summary)

    return allowed


def _sanitize_against_bundle(markdown_text: str, bundle: EvidenceBundle) -> str:
    text = (markdown_text or "").strip()
    if not text:
        return ""

    allowed_terms = _collect_allowed_terms(bundle)

    def _strip_capitalized(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.lower() in allowed_terms:
            return token
        return ""

    def _strip_dates(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.lower() in allowed_terms:
            return token
        return ""

    text = _DATE_TOKEN_PATTERN.sub(_strip_dates, text)
    text = _CAPITALIZED_TOKEN_PATTERN.sub(_strip_capitalized, text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

class TemplateGenerationError(Exception):
    """Raised when a template-based report cannot be generated."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


REPORT_TASK_INSTRUCTIONS = (
    "You are an intelligence reporting assistant generating a mission-ready product."
    "\n- Use the supplied mission context, structured intel, and knowledge graph metrics only."
    "\n- Enforce all authority and INT guardrails before writing."
    "\n- Follow the selected template's structure and tone exactly, filling every required section."
)


def _build_report_system_prompt(
    mission_context: Dict[str, Any],
    template: InternalReportTemplate,
) -> str:
    instructions = (
        f"Template: {template.name} (id={template.id}, INT={template.int_type or 'unspecified'})\n"
        f"Purpose: {template.description or 'No description provided.'}\n"
        f"{REPORT_TASK_INSTRUCTIONS}\n{_TEMPLATE_FILL_RULES}"
    )
    return build_global_system_prompt(mission_context, instructions)


class TemplateReportService:
    def __init__(
        self,
        db: Session,
        *,
        template_service: TemplateService | None = None,
        context_service: MissionContextService | None = None,
        llm_client: LLMClient | None = None,
        decision_service: DecisionDatasetService | None = None,
    ) -> None:
        self.db = db
        self._template_service = template_service or TemplateService()
        self._context_service = context_service or MissionContextService(db)
        self._llm = llm_client or LLMClient()
        self._decision_service = decision_service or DecisionDatasetService(db, context_service=self._context_service)

    def list_templates(self) -> list[InternalReportTemplate]:
        return self._template_service.list_templates()

    def get_template(self, template_id: str) -> InternalReportTemplate:
        return self._template_service.get_template(template_id)

    def list_templates_for_mission(self, mission: models.Mission) -> list[InternalReportTemplate]:
        templates = self._template_service.list_templates()
        return filter_templates_for_mission(mission=mission, templates=templates)

    def generate_report(self, mission_id: int, template_id: str) -> Dict[str, Any]:
        mission = self._get_mission(mission_id)
        logger.info(
            "template_report.generate.start",
            extra={
                "mission_id": mission_id,
                "template_id": template_id,
                "mission_authority": mission.mission_authority,
            },
        )

        evidence_bundle = self._get_evidence_bundle(mission.id)
        logger.debug(
            "template_report.evidence_bundle",
            extra={
                "mission_id": mission.id,
                "template_id": template_id,
                "incidents": len(evidence_bundle.incidents),
                "subjects": len(evidence_bundle.subjects),
                "documents": len(evidence_bundle.documents),
            },
        )
        try:
            template = self._template_service.get_template(template_id)
        except TemplateDefinitionNotFound as exc:
            logger.warning(
                "template_report.generate.template_missing",
                extra={"mission_id": mission_id, "template_id": template_id},
            )
            raise TemplateGenerationError("Template not found", status_code=404) from exc

        allowed = filter_templates_for_mission(mission=mission, templates=[template])
        if not allowed:
            logger.warning(
                "template_report.generate.unauthorized",
                extra={
                    "mission_id": mission_id,
                    "template_id": template_id,
                    "mission_authority": mission.mission_authority,
                },
            )
            raise TemplateGenerationError(
                "Template is not authorized for this mission's authority",
                status_code=403,
            )

        try:
            context = self._context_service.build_context_for_mission(mission)
        except MissionContextError as exc:  # pragma: no cover - simple propagation
            logger.exception("Failed to build mission context for mission_id=%s", mission_id)
            raise TemplateGenerationError("Unable to build mission context", status_code=500) from exc

        kg_summary = summarize_kg_snapshot(context.get("kg_snapshot"))
        context["kg_snapshot_summary"] = kg_summary
        logger.info(
            "template_report.context.ready",
            extra={
                "mission_id": mission_id,
                "template_id": template_id,
                "has_kg_summary": bool(kg_summary),
            },
        )

        if template.id == "leo_case_summary_v1":
            return self._generate_leo_case_summary(
                mission=mission,
                template=template,
                context=context,
            )

        if template.id == "osint_pattern_of_life_leo_v1":
            return self._generate_osint_pol_leo(
                mission=mission,
                template=template,
                context=context,
            )

        if template.id == "full_intrep_v1":
            return self._generate_full_intrep(
                mission=mission,
                template=template,
                context=context,
            )

        if template.id == "delta_update_v1":
            return self._generate_delta_update(
                mission=mission,
                template=template,
                context=context,
            )

        if template.id == "commander_decision_sheet_v1":
            decision_dataset = self._decision_service.build_decision_dataset(
                mission=mission,
                context=context,
            )
            return self._generate_commander_decision_sheet(
                mission=mission,
                template=template,
                decision_dataset=decision_dataset,
                context=context,
            )

        raise TemplateGenerationError(
            "Template engine not yet implemented for this template",
            status_code=501,
        )

    def _parse_llm_response(self, raw: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")
            return data, {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM response was not valid JSON", exc_info=True)
            return {}, {"raw_text": raw, "parse_error": str(exc)}

    def _get_mission(self, mission_id: int) -> models.Mission:
        mission = self.db.query(models.Mission).filter(models.Mission.id == mission_id).first()
        if not mission:
            raise TemplateGenerationError("Mission not found", status_code=404)
        return mission

    def _render_markdown(self, md: str) -> str:
        rendered = markdown2.markdown(
            md,
            extras=[
                "fenced-code-blocks",
                "tables",
                "strike",
                "underline",
                "nofollow",
            ],
        )
        return _strip_placeholders(rendered)

    def _fetch_agent_run(
        self,
        mission: models.Mission,
        run_payload: Dict[str, Any] | None,
    ) -> models.AgentRun | None:
        if not run_payload or not isinstance(run_payload, dict):
            return None
        run_id = run_payload.get("id")
        if not run_id:
            return None
        return (
            self.db.query(models.AgentRun)
            .filter(models.AgentRun.id == run_id, models.AgentRun.mission_id == mission.id)
            .first()
        )

    def _serialize_agent_run(self, run: models.AgentRun | None) -> Dict[str, Any] | None:
        if not run:
            return None
        return {
            "id": run.id,
            "summary": run.summary,
            "next_steps": run.next_steps,
            "guardrail_status": run.guardrail_status,
            "guardrail_issues": list(run.guardrail_issues or []),
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        }

    def _build_evidence_summary(
        self,
        *,
        mission: models.Mission,
    ) -> Dict[str, Any]:
        incidents: list[Dict[str, Any]] = []
        for event in getattr(mission, "events", []) or []:
            incidents.append(
                {
                    "id": getattr(event, "id", None),
                    "datetime": getattr(event, "timestamp", None).isoformat() if getattr(event, "timestamp", None) else None,
                    "location": getattr(event, "location", None) or getattr(event, "location_name", None),
                    "summary": getattr(event, "summary", None) or getattr(event, "description", None),
                    "sources": [getattr(doc, "id", None) for doc in getattr(event, "documents", []) or []],
                }
            )

        osint_items: list[Dict[str, Any]] = []
        finint_items: list[Dict[str, Any]] = []
        cctv_items: list[Dict[str, Any]] = []
        other_items: list[Dict[str, Any]] = []

        for doc in getattr(mission, "documents", []) or []:
            tags = {value.upper() for value in (getattr(doc, "int_types", None) or []) if value}
            doc_payload = {
                "id": getattr(doc, "id", None),
                "title": getattr(doc, "title", None),
                "summary": getattr(doc, "summary", None) or getattr(doc, "content", "")[:500],
                "metadata": getattr(doc, "metadata", None) or {},
            }
            if "OSINT" in tags:
                osint_items.append(doc_payload)
            elif "FININT" in tags:
                finint_items.append(doc_payload)
            elif tags.intersection({"CCTV", "IMAGERY"}):
                cctv_items.append(doc_payload)
            else:
                other_items.append(doc_payload)

        vehicles: list[Dict[str, Any]] = []
        for entity in getattr(mission, "entities", []) or []:
            if getattr(entity, "entity_type", None) == "VEHICLE":
                attrs = getattr(entity, "attributes", None) or {}
                vehicles.append(
                    {
                        "id": getattr(entity, "id", None),
                        "description": getattr(entity, "name", None),
                        "plate": attrs.get("plate"),
                        "color": attrs.get("color"),
                    }
                )

        return {
            "incidents": incidents,
            "osint": osint_items,
            "finint": finint_items,
            "cctv": cctv_items,
            "other": other_items,
            "vehicles": vehicles,
        }

    def _serialize_mission(self, mission: models.Mission) -> Dict[str, Any]:
        return {
            "id": mission.id,
            "name": getattr(mission, "name", None),
            "authority": getattr(mission, "mission_authority", None),
            "int_lanes": list(mission.int_types or []),
            "created_at": mission.created_at.isoformat() if mission.created_at else None,
            "updated_at": mission.updated_at.isoformat() if mission.updated_at else None,
        }

    def _build_prompt_context(
        self,
        *,
        mission: models.Mission,
        agent_run: models.AgentRun | None,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Milestone 1: agent_run content is intentionally excluded from prompt context to keep reports
        # grounded only in structured mission data. agent_run remains available solely for metadata/UI.
        return {
            "mission": self._serialize_mission(mission),
            "documents": context.get("documents"),
            "entities": context.get("entities"),
            "events": context.get("events"),
            "datasets": context.get("datasets"),
            "gap_analysis": context.get("gap_analysis"),
            "kg_snapshot_summary": context.get("kg_snapshot_summary"),
        }

    def _base_metadata(
        self,
        *,
        template: InternalReportTemplate,
        agent_run: models.AgentRun | Dict[str, Any] | None = None,
        kg_summary: Optional[str],
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "template_int_type": template.int_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if agent_run:
            if isinstance(agent_run, models.AgentRun):
                metadata["latest_agent_run"] = self._serialize_agent_run(agent_run)
            elif isinstance(agent_run, dict):
                metadata["latest_agent_run"] = agent_run
        if kg_summary is not None:
            metadata["kg_snapshot_summary"] = kg_summary
        return metadata

    def _format_report_result(
        self,
        *,
        mission: models.Mission,
        template: InternalReportTemplate,
        html: str,
        markdown: str | None,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "mission_id": mission.id,
            "template_id": template.id,
            "template_name": template.name,
            "html": html,
            "markdown": markdown,
            "metadata": metadata,
        }

    def _get_evidence_bundle(self, mission_id: int) -> EvidenceBundle:
        extractor = EvidenceExtractorService(session=self.db)
        return extractor.build_evidence_bundle(mission_id)

    def _bundle_has_evidence(self, bundle: EvidenceBundle) -> bool:
        """
        Return True if the EvidenceBundle contains any concrete evidence.
        We treat any non-empty list as evidence: incidents, subjects, events,
        documents, gaps, or a non-empty KG summary.
        """

        if not bundle:
            return False

        if bundle.incidents:
            return True
        if bundle.subjects:
            return True
        if bundle.events:
            return True
        if bundle.documents:
            return True
        if bundle.gaps:
            return True

        kg_summary = getattr(bundle, "kg_summary", None)
        if kg_summary is None:
            kg_summary = getattr(bundle, "kg_snapshot_summary", None)
        if isinstance(kg_summary, str) and kg_summary.strip():
            return True

        return False

    def _build_empty_leo_report(self, bundle: EvidenceBundle) -> str:
        mission_name = bundle.mission_name or "Mission"
        authority = bundle.authority or "LEO"
        lanes = ", ".join(bundle.int_lanes) if bundle.int_lanes else "Not specified"
        report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        none_line = "None available based on current evidence."

        sections = [
            f"# LEO CASE SUMMARY – {mission_name}",
            "",
            f"**Mission:** {mission_name}",
            f"**Authority:** {authority}",
            f"**INT Lanes:** {lanes}",
            f"**Prepared by:** EvidenceBundle Guardrail",
            f"**Date:** {report_date}",
            "",
            "---",
            "",
            "## 1. Key Judgments",
            f"- {none_line}",
            "",
            "---",
            "",
            "## 2. Incident Overview",
            "### 2.1 Confirmed Incidents",
            f"- {none_line}",
            "",
            "### 2.2 Patterns",
            f"- {none_line}",
            "",
            "---",
            "",
            "## 3. Subjects & Associates",
            "### 3.1 Primary Subjects",
            f"- {none_line}",
            "",
            "### 3.2 Associates / Linked Identities",
            f"- {none_line}",
            "",
            "---",
            "",
            "## 4. Modus Operandi",
            f"- {none_line}",
            "",
            "---",
            "",
            "## 5. Evidence & Corroboration",
            f"- {none_line}",
            "",
            "---",
            "",
            "## 6. Gaps & Constraints",
            f"- {none_line}",
            "",
            "---",
            "",
            "## 7. Recommended Actions (LEO)",
            f"- {none_line}",
            "",
            "---",
            "",
            "## 8. Risk & Civil Liberties Considerations",
            f"- {none_line}",
        ]

        return "\n".join(sections)

    def _invoke_markdown_llm(self, system_prompt: str, user_prompt: str, *, template_id: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            logger.info("template_report.llm.invoke", extra={"template_id": template_id})
            response = self._llm.chat(messages)
        except LlmError as exc:
            logger.exception("LLM call failed for template_id=%s", template_id)
            raise TemplateGenerationError("LLM call failed", status_code=502) from exc
        return response.strip()

    def _generate_leo_case_summary(
        self,
        *,
        mission: models.Mission,
        template: InternalReportTemplate,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        bundle = self._get_evidence_bundle(mission.id)
        if not self._bundle_has_evidence(bundle):
            markdown_output = _clean_markdown_output(self._build_empty_leo_report(bundle))
        else:
            evidence_payload = {
                "incidents": [incident.model_dump() for incident in bundle.incidents],
                "subjects": [subject.model_dump() for subject in bundle.subjects],
                "associates": [assoc.model_dump() for assoc in bundle.associates],
                "locations": [location.model_dump() for location in bundle.locations],
                "events": [event.model_dump() for event in bundle.events],
                "documents": [doc.model_dump() for doc in bundle.documents],
                "gaps": [gap.model_dump() for gap in bundle.gaps],
            }
            ctx_json = json.dumps(evidence_payload, ensure_ascii=False, indent=2, default=str)

            system_prompt = (
                "You are a law-enforcement intelligence analyst producing a structured case summary.\n"
                "Use ONLY the structured evidence bundle provided in JSON.\n"
                "You are forbidden from inventing incidents, subjects, organizations, locations, or dates.\n"
                "You must not mention 'mission text', 'provided data', 'initial analysis', 'analysis agent', 'agent advisory', 'publicly available data', or similar phrases.\n"
                "You must not invent organizations, places, suspects, facilities, or behaviors beyond the evidence bundle.\n"
                "You must not guess dates or infer entities/relationships not explicitly present.\n"
                "If a list is empty, write 'None available based on current evidence'.\n"
                f"Treat the mission authority as '{mission.mission_authority}' only.\n"
                "Never mention variable names or Event IDs.\n"
                "Do not include instructions like 'Provide HIGH/MEDIUM/LOW'.\n"
                "If you lack information, respond with 'None available based on current evidence'.\n"
                "Follow the markdown skeleton exactly and keep a professional LEO tone."
            )

            user_prompt = (
                "You will receive a JSON object named EVIDENCE with incidents, subjects, associates, locations, events, documents, and gaps.\n"
                "Use only these fields.\n"
                "If a section has no data, state 'None available based on current evidence'.\n"
                "Do NOT invent or reference anything outside the JSON.\n"
                "Avoid meta references, array indices, or mention of JSON/context.\n\n"
                "EVIDENCE JSON:\n"
                f"{ctx_json}\n\n"
                "MARKDOWN SKELETON:\n"
                f"{template.markdown_skeleton}\n"
                "Fill every section with evidence-backed prose."
            )

            markdown_output = _clean_markdown_output(
                self._invoke_markdown_llm(system_prompt, user_prompt, template_id=template.id)
            )

        markdown_output = _sanitize_report_markdown(markdown_output)
        markdown_output = _sanitize_against_bundle(markdown_output, bundle)
        if not markdown_output:
            raise TemplateGenerationError("LLM returned empty output", status_code=502)

        html_output = self._render_markdown(markdown_output)
        metadata = self._base_metadata(template=template, kg_summary=context.get("kg_snapshot_summary"))

        logger.info(
            "template_report.generate.success",
            extra={
                "mission_id": mission.id,
                "template_id": template.id,
                "render_mode": "markdown",
            },
        )

        return self._format_report_result(
            mission=mission,
            template=template,
            html=html_output,
            markdown=markdown_output,
            metadata=metadata,
        )

    def _generate_commander_decision_sheet(
        self,
        *,
        mission: models.Mission,
        template: InternalReportTemplate,
        context: Dict[str, Any],
        decision_dataset: DecisionDataset | None,
    ) -> Dict[str, Any]:
        ctx = self._build_prompt_context(mission=mission, agent_run=None, context=context)
        if decision_dataset:
            ctx["decisions"] = (
                decision_dataset.model_dump()
                if hasattr(decision_dataset, "model_dump")
                else decision_dataset
            )
        else:
            ctx["decisions"] = {
                "decisions": [],
                "courses_of_action": [],
                "policy_checks": [],
                "blind_spots": [],
                "precedents": [],
            }

        ctx_json = json.dumps(ctx, ensure_ascii=False, indent=2, default=str)

        system_prompt = (
            "You are a staff officer generating a Commander Decision Sheet based on a structured decision dataset. "
            "Use the provided markdown skeleton to present key decision questions, the system-recommended course of action, alternative COAs with pros and cons, "
            "policy/legal checks, blind spots, and overall confidence. Do NOT invent new decisions, policies, or COAs; stay strictly within the provided dataset. "
            "Write concisely for a commander who must choose quickly."
        )

        user_prompt = (
            "CONTEXT (JSON):\n"
            f"{ctx_json}\n\n"
            "TASK:\n"
            "Using the decisions.decisions, decisions.courses_of_action, decisions.policy_checks, and decisions.blind_spots arrays, fill in the Commander Decision Sheet markdown template below.\n"
            "Preserve all headings and their order exactly.\n\n"
            "TEMPLATE:\n"
            f"{template.markdown_skeleton}\n"
        )

        markdown_output = self._invoke_markdown_llm(system_prompt, user_prompt, template_id=template.id)
        if not markdown_output:
            raise TemplateGenerationError("LLM returned empty output", status_code=502)
        markdown_output = self._strip_placeholders(markdown_output)
        markdown_output = _sanitize_report_markdown(markdown_output)
        html_output = self._render_markdown(markdown_output)
        metadata = self._base_metadata(
            template=template,
            agent_run=agent_run,
            kg_summary=context.get("kg_snapshot_summary"),
        )
        if decision_dataset:
            metadata["decisions"] = (
                decision_dataset.model_dump()
                if hasattr(decision_dataset, "model_dump")
                else decision_dataset
            )
        else:
            metadata["decisions"] = None

        return self._format_report_result(
            mission=mission,
            template=template,
            html=html_output,
            markdown=markdown_output,
            metadata=metadata,
        )

    def _generate_osint_pol_leo(
        self,
        *,
        mission: models.Mission,
        template: InternalReportTemplate,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        ctx = self._build_prompt_context(mission=mission, agent_run=None, context=context)
        ctx_json = json.dumps(ctx, ensure_ascii=False, indent=2, default=str)

        system_prompt = (
            "You are an open-source intelligence (OSINT) analyst supporting law enforcement. "
            "Generate an OSINT Pattern of Life report in markdown using the provided skeleton. "
            "Focus on subject identifiers, accounts, platforms, behavior over time, locations, network affiliations, and risk indicators. "
            "Stay strictly within OSINT and lawful LE procedures. Do NOT recommend illegal surveillance or intelligence-community collection authorities."
        )

        user_prompt = (
            "CONTEXT (JSON):\n"
            f"{ctx_json}\n\n"
            "TASK:\n"
            "Fill in the following markdown template for an OSINT Pattern of Life report for law enforcement.\n"
            "Replace all {{placeholders}} with concrete content based on the context only.\n"
            "Preserve all headings and section order exactly.\n\n"
            "TEMPLATE:\n"
            f"{template.markdown_skeleton}\n"
        )

        markdown_output = self._invoke_markdown_llm(system_prompt, user_prompt, template_id=template.id)
        if not markdown_output:
            raise TemplateGenerationError("LLM returned empty output", status_code=502)
        markdown_output = _sanitize_report_markdown(_strip_placeholders(markdown_output))
        html_output = self._render_markdown(markdown_output)
        metadata = self._base_metadata(template=template, agent_run=agent_run, kg_summary=context.get("kg_snapshot_summary"))

        return {
            "mission_id": mission.id,
            "template_id": template.id,
            "template_name": template.name,
            "html": html_output,
            "markdown": markdown_output,
            "metadata": metadata,
        }

    def _generate_full_intrep(
        self,
        *,
        mission: models.Mission,
        template: InternalReportTemplate,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        agent_run = context.get("latest_agent_run") or context.get("agent_run")
        ctx = self._build_prompt_context(mission=mission, agent_run=None, context=context)
        ctx_json = json.dumps(ctx, ensure_ascii=False, indent=2, default=str)

        system_prompt = (
            "You are an intelligence analyst preparing a formal intelligence report (INTREP). "
            "Generate a structured report in markdown using the provided skeleton. "
            "Include situation/context, the intelligence picture, assessments and judgments with stated confidence levels, high-level courses of action, gaps, and risks. "
            "Use clear analytic language and avoid recommending specific operational tasking beyond what the context clearly supports."
        )

        user_prompt = (
            "CONTEXT (JSON):\n"
            f"{ctx_json}\n\n"
            "TASK:\n"
            "Fill in the following markdown template for an Intelligence Report (INTREP).\n"
            "Replace all {{placeholders}} with content grounded in the context only.\n"
            "Preserve headings and section order exactly.\n\n"
            "TEMPLATE:\n"
            f"{template.markdown_skeleton}\n"
        )

        markdown_output = self._invoke_markdown_llm(system_prompt, user_prompt, template_id=template.id)
        if not markdown_output:
            raise TemplateGenerationError("LLM returned empty output", status_code=502)

        html_output = self._render_markdown(markdown_output)
        metadata = self._base_metadata(template=template, agent_run=agent_run, kg_summary=context.get("kg_snapshot_summary"))

        return {
            "mission_id": mission.id,
            "template_id": template.id,
            "template_name": template.name,
            "html": html_output,
            "markdown": markdown_output,
            "metadata": metadata,
        }

    def _get_previous_agent_run(self, mission: models.Mission, current_run: models.AgentRun | None) -> models.AgentRun | None:
        query = (
            self.db.query(models.AgentRun)
            .filter(models.AgentRun.mission_id == mission.id)
            .order_by(models.AgentRun.created_at.desc())
        )
        if current_run:
            query = query.filter(models.AgentRun.id != current_run.id)
        return query.first()

    def _generate_delta_update(
        self,
        *,
        mission: models.Mission,
        template: InternalReportTemplate,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        agent_run = context.get("latest_agent_run") or context.get("agent_run")
        previous_run = self._get_previous_agent_run(mission, None)
        ctx = self._build_prompt_context(mission=mission, agent_run=None, context=context)
        ctx["delta_metadata"] = {
            "latest_run_id": getattr(agent_run, "id", None),
            "latest_run_timestamp": getattr(agent_run, "created_at", None).isoformat() if getattr(agent_run, "created_at", None) else None,
            "previous_run_id": getattr(previous_run, "id", None),
            "previous_run_timestamp": getattr(previous_run, "created_at", None).isoformat() if getattr(previous_run, "created_at", None) else None,
        }
        ctx_json = json.dumps(ctx, ensure_ascii=False, indent=2, default=str)

        system_prompt = (
            "You are an intelligence analyst preparing a Delta Update report. "
            "Your job is to describe what has CHANGED since the previous run or report. "
            "Highlight new facts, updated assessments, newly identified gaps, and updated recommended actions. "
            "Do not restate the entire original case; focus on deltas."
        )

        user_prompt = (
            "CONTEXT (JSON):\n"
            f"{ctx_json}\n\n"
            "TASK:\n"
            "Fill in the Delta Update markdown template below, focusing ONLY on changes since the previous run.\n"
            "Replace all {{placeholders}} with change-focused content based on the context.\n\n"
            "TEMPLATE:\n"
            f"{template.markdown_skeleton}\n"
        )

        markdown_output = self._invoke_markdown_llm(system_prompt, user_prompt, template_id=template.id)
        if not markdown_output:
            raise TemplateGenerationError("LLM returned empty output", status_code=502)

        html_output = self._render_markdown(markdown_output)
        metadata = self._base_metadata(
            template=template,
            agent_run=agent_run,
            kg_summary=context.get("kg_snapshot_summary"),
        )
        if previous_run:
            metadata["previous_agent_run"] = self._serialize_agent_run(previous_run)

        return self._format_report_result(
            mission=mission,
            template=template,
            html=html_output,
            markdown=markdown_output,
            metadata=metadata,
        )
