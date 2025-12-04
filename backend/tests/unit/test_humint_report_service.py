# core/APEX/backend/tests/unit/test_humint_report_service.py

import pytest
from typing import Dict, Any

from app.services.humint_report_service import HumintReportService
from app.models.humint_report import HumintReport
from app.models.humint_insight import HumintInsight
from app.models.humint_followup import HumintFollowUpPlan
from app.db.session import SessionLocal, Base, engine


class FakeExtractionEntity:
    def __init__(self, name: str, kg_id: str | None = None):
        self.name = name
        self.kg_id = kg_id
        self.roles: list[str] = []
        self.source_section_ids: list[str] = []


class FakeExtractionEvent:
    def __init__(self, description: str):
        self.description = description
        self.time = None
        self.location = None
        self.participant_ids: list[str] = []
        self.kg_id = None
        self.source_section_ids: list[str] = []


class FakeExtractionResult:
    def __init__(self):
        self.entities: list[FakeExtractionEntity] = []
        self.events: list[FakeExtractionEvent] = []


class FakeBundle:
    def __init__(self, bundle_id: int):
        self.id = bundle_id


class FakeEvidenceBundleService:
    """
    Minimal stub for EvidenceBundleService so we don't hit any real pipelines.
    """

    def __init__(self, db):
        self.db = db
        self._next_id = 1

    def create_temporary_bundle_from_text(self, text: str) -> FakeBundle:
        bundle = FakeBundle(self._next_id)
        self._next_id += 1
        return bundle

    def run_extraction(self, bundle_id: int) -> FakeExtractionResult:
        result = FakeExtractionResult()
        result.entities.append(FakeExtractionEntity(name="SOURCE A", kg_id="ent-1"))
        result.events.append(FakeExtractionEvent(description="SOURCE A observed a meeting."))
        return result


class FakeLlmClient:
    """
    Stub LLM that returns deterministic JSON for both section parsing and follow-up plan.
    """

    def ask_json(self, prompt: str) -> Dict[str, Any]:
        if "TEMPLATE SECTIONS" in prompt:
            return {
                "header": "DTG: 20250101Z\nUnit: TEST UNIT",
                "bluf": "Source reports an upcoming meeting between targets in CITY X.",
                "exec_summary": "Source A reported an upcoming meeting between key targets in CITY X within 48 hours.",
                "source_reporting": "Source A stated that SUBJECT 1 will meet SUBJECT 2 at a safe location in CITY X.",
            }
        return {
            "objective_summary": "Clarify details of the planned meeting in CITY X and validate source access.",
            "next_interview_questions": [
                {
                    "questionText": "Precisely when and where will the meeting in CITY X occur?",
                    "rationale": "Time and location are critical for corroboration and cross-cueing.",
                    "priority": "high",
                },
                {
                    "questionText": "How does the source know these individuals and how did they learn of the meeting?",
                    "rationale": "Understand access and potential deception risk.",
                    "priority": "medium",
                },
            ],
            "verification_tasks": [
                {
                    "type": "OSINT",
                    "description": "Check local open-source reporting for announcements or events near the stated meeting time/location.",
                    "priority": "low",
                },
                {
                    "type": "SIGINT",
                    "description": "Review recent communications associated with SUBJECT 1 and SUBJECT 2 for indicators of travel or coordination.",
                    "priority": "medium",
                },
            ],
            "engagement_notes": [
                {
                    "noteText": "Maintain established rapport; avoid pressing too hard on personal vulnerabilities during this session.",
                    "category": "rapport",
                }
            ],
        }


class FakeKgClient:
    """
    Stub KG client with fixed scores to make assertions easy and predictable.
    """

    def compute_novelty(self, **kwargs) -> float:
        return 0.8

    def compute_corroboration(self, **kwargs) -> float:
        return 0.4

    def compute_relevance_to_mission(self, **kwargs) -> float:
        return 0.9


class TestHumintReportService:
    @pytest.fixture
    def db(self):
        Base.metadata.create_all(bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def service(self, db):
        svc = HumintReportService(db=db)
        svc.llm = FakeLlmClient()
        svc.kg = FakeKgClient()
        svc.bundle_service = FakeEvidenceBundleService(db)
        return svc

    def test_ingest_creates_report_insights_and_followup(self, service):
        raw_iir = """
CLASSIFIED//REL TO USA

BLUF: Source reports an upcoming meeting between key targets in CITY X.

Source A stated that SUBJECT 1 will meet SUBJECT 2 at a safe location in CITY X within the next 48 hours.
The meeting is reportedly tied to planning hostile activity against coalition logistics.

End report.
"""

        result = service.ingest(raw_text=raw_iir, mission_id=None)

        report = result["report"]
        insights = result["insights"]
        followup = result["followup_plan"]

        assert isinstance(report, HumintReport)
        assert isinstance(insights, list)
        assert len(insights) > 0
        assert isinstance(followup, HumintFollowUpPlan)

        assert "bluf" in report.structured_sections
        assert "Source reports an upcoming meeting" in report.structured_sections["bluf"]

        insight = insights[0]
        assert isinstance(insight, HumintInsight)
        assert insight.novelty_score == pytest.approx(0.8)
        assert insight.operational_relevance == pytest.approx(0.9)

        assert "meeting in CITY X" in followup.objective_summary
        assert len(followup.next_interview_questions) >= 1
        assert followup.next_interview_questions[0]["priority"] in ("low", "medium", "high")
        assert len(followup.verification_tasks) >= 1
        assert followup.engagement_notes[0]["category"] in ("rapport", "safety", "cover", "other")
