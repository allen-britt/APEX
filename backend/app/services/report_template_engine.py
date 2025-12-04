from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import models
from app.services.kg_snapshot_utils import summarize_kg_snapshot
from app.services.llm_client import _with_llm_fallback

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "report_templates.json"


@dataclass
class TemplateSection:
    id: str
    title: str
    prompt: str
    purpose: Optional[str] = None
    prompt_role: Optional[str] = None


@dataclass
class ReportTemplate:
    id: str
    name: str
    description: str = ""
    int_type: Optional[str] = None
    sections: List[TemplateSection] = field(default_factory=list)
    mission_domains: List[str] = field(default_factory=list)
    title10_allowed: bool = False
    title50_allowed: bool = False

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "int_type": self.int_type,
            "mission_domains": list(self.mission_domains),
            "title10_allowed": self.title10_allowed,
            "title50_allowed": self.title50_allowed,
            "sections": [section.title for section in self.sections],
        }


class TemplateNotFoundError(Exception):
    pass


class ReportTemplateEngine:
    def __init__(self, *, template_path: Path | None = None) -> None:
        self._template_path = template_path or TEMPLATE_PATH
        self._templates = self._load_templates()

    def _load_templates(self) -> Dict[str, ReportTemplate]:
        if not self._template_path.exists():
            raise FileNotFoundError(f"Template config not found: {self._template_path}")
        raw = json.loads(self._template_path.read_text(encoding="utf-8"))
        templates: Dict[str, ReportTemplate] = {}
        for entry in raw:
            sections = [TemplateSection(**section) for section in entry.get("sections", [])]
            template = ReportTemplate(
                id=entry["id"],
                name=entry.get("name", entry["id"]),
                description=entry.get("description", ""),
                int_type=entry.get("int_type"),
                mission_domains=entry.get("mission_domains", []) or [],
                title10_allowed=bool(entry.get("title10_allowed", False)),
                title50_allowed=bool(entry.get("title50_allowed", False)),
                sections=sections,
            )
            templates[template.id] = template
        return templates

    def list_templates(self) -> List[Dict[str, Any]]:
        return [tpl.to_summary() for tpl in self._templates.values()]

    def get_template(self, template_id: str) -> ReportTemplate:
        template = self._templates.get(template_id)
        if not template:
            raise TemplateNotFoundError(f"Unknown template id: {template_id}")
        return template

    def get_all_templates(self) -> List[ReportTemplate]:
        return list(self._templates.values())

    async def render_template(
        self,
        *,
        template_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        template = self.get_template(template_id)

        mission_block = _ensure_mapping(context.get("mission"))
        documents = _ensure_list(context.get("documents"))
        entities = _ensure_list(context.get("entities"))
        events = _ensure_list(context.get("events"))
        datasets = _ensure_list(context.get("datasets"))
        gap_analysis = context.get("gap_analysis")
        latest_run = _ensure_mapping(context.get("latest_agent_run"))
        kg_snapshot_summary = context.get("kg_snapshot_summary") or summarize_kg_snapshot(
            context.get("kg_snapshot")
        )

        base_payload: Dict[str, Any] = {
            "mission": mission_block,
            "documents": documents,
            "entities": entities,
            "events": events,
            "datasets": datasets,
            "gap_analysis": gap_analysis,
            "kg_snapshot_summary": kg_snapshot_summary,
            "latest_agent_run": latest_run or None,
        }

        sections_output: List[Dict[str, Any]] = []
        for section in template.sections:
            section_payload = dict(base_payload)
            section_payload["section"] = {
                "id": section.id,
                "title": section.title,
                "purpose": section.purpose,
                "prompt_role": section.prompt_role,
            }
            prompt = (
                f"Section: {section.title}\n"
                f"Instruction: {section.prompt}\n"
                "Context JSON follows. Respond with concise prose or bullets and avoid markdown headings unless necessary.\n"
                f"Context:\n{json.dumps(section_payload, ensure_ascii=False, indent=2)}"
            )
            content = await _with_llm_fallback(
                prompt=prompt,
                system="You are an intelligence briefer generating structured sections.",
                parse=lambda raw: raw,
                stub=lambda: f"Stubbed content for {section.title}",
            )
            sections_output.append({"id": section.id, "title": section.title, "content": content})

        metadata: Dict[str, Any] = {"generated_at": datetime.utcnow().isoformat()}
        if kg_snapshot_summary:
            metadata["kg_snapshot_summary"] = kg_snapshot_summary
        if latest_run:
            metadata["latest_agent_run"] = latest_run
            metadata["guardrail_status"] = latest_run.get("guardrail_status")
            metadata["guardrail_issues"] = list(latest_run.get("guardrail_issues") or [])

        return {
            "template_id": template.id,
            "template_name": template.name,
            "sections": sections_output,
            "metadata": metadata,
        }


def _ensure_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []
