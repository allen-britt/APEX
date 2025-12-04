# backend/app/services/humint_report_service.py

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.humint.templates import HUMINT_TEMPLATES, HumintTemplateDefinition
from app.db.session import SessionLocal

# Models (these two will be created below)
from app.models.humint_report import HumintReport
from app.models.humint_insight import HumintInsight
from app.models.humint_followup import HumintFollowUpPlan

# Placeholder imports for LLM and KG clients
# Replace with your actual implementations
class LlmClient:
    def ask_json(self, prompt: str) -> Dict[str, Any]:
        raise NotImplementedError("LLM integration not implemented yet")


class KgClient:
    def compute_novelty(self, **kwargs):
        return 0.0

    def compute_corroboration(self, **kwargs):
        return 0.0

    def compute_relevance_to_mission(self, **kwargs):
        return 0.0


class EvidenceBundleService:
    def __init__(self, db):
        self.db = db

    def create_temporary_bundle_from_text(self, text):
        raise NotImplementedError

    def run_extraction(self, bundle_id):
        raise NotImplementedError


class HumintReportService:
    """
    Skeleton service for HUMINT report ingestion and analysis.
    Implementations will be added in follow-up steps.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
        self.llm = LlmClient()
        self.kg = KgClient()
        self.bundle_service = EvidenceBundleService(self.db)

    def _find_template_by_id(self, template_id: str) -> HumintTemplateDefinition:
        for template in HUMINT_TEMPLATES:
            if template["id"] == template_id:
                return template
        raise ValueError(f"Unknown HUMINT template id: {template_id}")

    def detect_template(self, raw_text: str) -> HumintTemplateDefinition:
        """
        Determine which HUMINT template is most appropriate based on simple heuristics.
        Default to the full Standard IIR.
        """
        lower = raw_text.lower()

        if "bluf" in lower and "executive summary" in lower:
            return self._find_template_by_id("HUMINT_IIR_STANDARD")

        if "spot report" in lower or "time-sensitive" in lower:
            return self._find_template_by_id("HUMINT_IIR_TACTICAL_SPOT")

        if "debrief" in lower or "session overview" in lower:
            return self._find_template_by_id("HUMINT_DEBRIEF_SUMMARY")

        if "source meeting" in lower or "contact report" in lower or "initial contact" in lower:
            return self._find_template_by_id("HUMINT_SOURCE_CONTACT")

        if "reliability" in lower or "validation" in lower or "track record" in lower:
            return self._find_template_by_id("HUMINT_SOURCE_VALIDATION")

        if "lead:" in lower or "leads:" in lower or "tip" in lower:
            return self._find_template_by_id("HUMINT_LEAD_SHEET")

        return self._find_template_by_id("HUMINT_IIR_STANDARD")

    def parse_into_sections(self, template: HumintTemplateDefinition, raw_text: str) -> Dict[str, str]:
        """
        Use the LLM to segment the incoming HUMINT report into structured sections.
        The LLM must not invent content; only relocate and trim existing content.
        """

        section_specs = [
            {"id": s["id"], "label": s["label"], "kind": s["kind"]}
            for s in template["sections"]
        ]

        prompt = f"""
You are a HUMINT reporting assistant. Your task is to map this HUMINT report into the template sections below.

TEMPLATE SECTIONS:
{section_specs}

RULES:
- Do NOT invent information.
- Only use text from the original report.
- Trim or group sentences if needed, but never fabricate.
- If a section has no corresponding text, return an empty string.
- Return a JSON object with keys matching the 'id' fields in the template.

ORIGINAL REPORT:
\"\"\"{raw_text}\"\"\"
"""

        llm_response = self.llm.ask_json(prompt)

        structured: Dict[str, str] = {}
        for s in template["sections"]:
            sid = s["id"]
            structured[sid] = llm_response.get(sid, "").strip()

        return structured

    def extract_entities_and_events(self, structured_sections: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Combine all section text and run the EvidenceBundle extraction pipeline.
        Return a normalized list of entities and events.
        """

        chunks = []
        for sid, content in structured_sections.items():
            if content:
                chunks.append(f"[{sid}]\n{content}")

        combined_text = "\n\n".join(chunks)

        # Create temporary bundle and run extraction
        bundle = self.bundle_service.create_temporary_bundle_from_text(combined_text)
        extraction = self.bundle_service.run_extraction(bundle.id)

        results: List[Dict[str, Any]] = []

        # Normalize entities
        for ent in getattr(extraction, "entities", []):
            results.append({
                "type": "entity",
                "name": ent.name,
                "kg_id": getattr(ent, "kg_id", None),
                "roles": getattr(ent, "roles", []),
                "source_section_ids": getattr(ent, "source_section_ids", []),
            })

        # Normalize events
        for evt in getattr(extraction, "events", []):
            results.append({
                "type": "event",
                "description": evt.description,
                "time": getattr(evt, "time", None),
                "location": getattr(evt, "location", None),
                "participants": getattr(evt, "participant_ids", []),
                "kg_id": getattr(evt, "kg_id", None),
                "source_section_ids": getattr(evt, "source_section_ids", []),
            })

        return results

    def compute_insights(self, extracted: List[Dict[str, Any]], report: HumintReport) -> List[HumintInsight]:
        """
        Score extracted elements for novelty, corroboration, relevance, and deception risk.
        """

        insights = []

        for item in extracted:
            description = item.get("description") or item.get("name")
            if not description:
                continue

            kg_id = item.get("kg_id")

            novelty = float(self.kg.compute_novelty(kg_id=kg_id, description=description))
            corroboration = float(self.kg.compute_corroboration(kg_id=kg_id, description=description))
            relevance = float(self.kg.compute_relevance_to_mission(kg_id=kg_id, mission_id=report.mission_id))

            time_sensitivity = "high" if item.get("time") else "low"

            deception_risk = "low"
            if novelty > 0.7 and corroboration < 0.3:
                deception_risk = "medium"

            insight = HumintInsight(
                report_id=report.id,
                description=description,
                novelty_score=novelty,
                corroboration_score=corroboration,
                operational_relevance=relevance,
                time_sensitivity=time_sensitivity,
                deception_risk=deception_risk,
                involved_entities=item.get("participants") or [kg_id] if kg_id else [],
                supporting_evidence={},
            )

            self.db.add(insight)
            insights.append(insight)

        self.db.commit()
        return insights

    def generate_followup_plan(
        self,
        report: HumintReport,
        insights: List[HumintInsight],
        structured_sections: Dict[str, str],
    ) -> HumintFollowUpPlan:
        """
        Use the LLM to generate a HUMINT SME–style follow-up action plan.
        """

        insights_payload = []
        for i in insights:
            insights_payload.append({
                "description": i.description,
                "novelty_score": i.novelty_score,
                "corroboration_score": i.corroboration_score,
                "operational_relevance": i.operational_relevance,
                "time_sensitivity": i.time_sensitivity,
                "deception_risk": i.deception_risk,
            })

        prompt = f"""
You are a senior HUMINT SME supporting a joint intelligence team (Army, DIA, SOF, IC).
Your task is to generate a FOLLOW-UP ACTION PLAN based strictly on:

1) The structured HUMINT report sections
2) The computed insights (novelty, corroboration, relevance, deception risk)

RULES:
- No invented facts.
- Questions must connect directly to insights or explicit gaps.
- Recommendations must be actionable at the next interview or via cross-cueing.
- Do not issue operational orders. Only collection-focused actions.
- Output JSON with this structure:

{{
  "objective_summary": "2-3 sentences",
  "next_interview_questions": [
    {{
      "questionText": "...",
      "rationale": "...",
      "priority": "low" | "medium" | "high"
    }}
  ],
  "verification_tasks": [
    {{
      "type": "HUMINT" | "OSINT" | "SIGINT" | "IMINT" | "DOCEXPLOIT" | "OTHER",
      "description": "...",
      "priority": "low" | "medium" | "high"
    }}
  ],
  "engagement_notes": [
    {{
      "noteText": "...",
      "category": "rapport" | "safety" | "cover" | "other"
    }}
  ]
}}

STRUCTURED SECTIONS:
{structured_sections}

INSIGHTS:
{insights_payload}
"""

        plan_json = self.llm.ask_json(prompt)

        plan = HumintFollowUpPlan(
            report_id=report.id,
            objective_summary=plan_json.get("objective_summary", "").strip(),
            next_interview_questions=plan_json.get("next_interview_questions", []),
            verification_tasks=plan_json.get("verification_tasks", []),
            engagement_notes=plan_json.get("engagement_notes", []),
        )

        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        return plan

    def ingest(self, raw_text: str, mission_id: Optional[int]):
        """
        Complete HUMINT pipeline:
        - Detect template
        - Parse report into sections
        - Store report
        - Extract entities/events
        - Compute insights
        - Generate follow-up plan
        - Return assembled data package
        """

        template = self.detect_template(raw_text)
        structured = self.parse_into_sections(template, raw_text)

        report = HumintReport(
            template_id=template["id"],
            raw_text=raw_text,
            structured_sections=structured,
            mission_id=mission_id,
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        extracted = self.extract_entities_and_events(structured)
        insights = self.compute_insights(extracted, report)
        followup = self.generate_followup_plan(report, insights, structured)

        return {
            "report": report,
            "insights": insights,
            "followup_plan": followup,
        }
