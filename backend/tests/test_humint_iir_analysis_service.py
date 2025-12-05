"""Tests for HumintIirAnalysisService plumbing."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import pytest

from app import models
from app.db.session import Base, SessionLocal, engine
from app.models.evidence import EvidenceBundle, EvidenceDocument
from app.services.humint_iir_analysis_service import HumintIirAnalysisService


class FakeExtractionService:
    async def extract_entities_and_events_for_mission(
        self,
        mission: models.Mission,
        documents: List[models.Document],
        profile: str = "humint",
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        return (
            [
                {
                    "name": "Source A",
                    "type": "person",
                    "description": "Field source",
                }
            ],
            [
                {
                    "title": "Meeting detected",
                    "summary": "Source observed a meeting",
                    "timestamp": None,
                    "location": "City X",
                    "involved_entity_ids": [],
                }
            ],
        )


class FakeEvidenceExtractor:
    def build_evidence_bundle(self, mission_id: int) -> EvidenceBundle:
        return EvidenceBundle(
            mission_id=str(mission_id),
            documents=[EvidenceDocument(id="42", title="Legacy Doc")],
        )


class FakeLLMClient:
    def chat(self, messages):  # pragma: no cover - deterministic stub
        payload = {
            "parsed_fields": {"summary": "SOURCE A"},
            "key_insights": [
                {
                    "title": "Targets planning activity",
                    "detail": "SOURCE A reports coordination in City X",
                    "confidence": 0.9,
                    "supporting_evidence_ids": [99],
                }
            ],
            "contradictions": ["No corroboration available"],
            "gaps": [
                {
                    "title": "Meeting timing",
                    "description": "Need precise timing",
                    "priority": 2,
                    "suggested_collection": "OSINT",
                }
            ],
            "followups": [
                {
                    "question": "When exactly will the meeting occur?",
                    "rationale": "Timing drives surveillance coverage",
                    "priority": 1,
                    "related_gap_titles": ["Meeting timing"],
                    "suggested_channel": "source_debrief",
                }
            ],
        }
        return json.dumps(payload)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.mark.asyncio
async def test_analyze_iir_returns_structured_result(db):
    mission = models.Mission(name="Test Mission", mission_authority="LEO")
    mission.int_types = ["HUMINT"]
    db.add(mission)
    db.commit()
    db.refresh(mission)

    document = models.Document(
        mission_id=mission.id,
        title="UNCLASS IIR",
        content="UNCLASSIFIED // Source observed coordination in City X",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    service = HumintIirAnalysisService(
        db=db,
        llm_client=FakeLLMClient(),
        extraction_service=FakeExtractionService(),
        evidence_extractor=FakeEvidenceExtractor(),
    )

    result = await service.analyze_iir(mission.id, document.id)

    assert result.mission_id == mission.id
    assert result.document_id == document.id
    assert result.parsed_fields.summary == "SOURCE A"
    assert result.key_insights and result.key_insights[0].confidence == pytest.approx(0.9)
    assert result.followups and result.followups[0].question.startswith("When")
    assert isinstance(result.contradictions, list)
    assert isinstance(result.evidence_document_ids, list)
