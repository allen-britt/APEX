"""API tests for HUMINT IIR analysis endpoint."""

from __future__ import annotations

from typing import AsyncIterator, Iterator, List, Tuple

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.api import humint as humint_api
from app.db.session import Base, get_db
from app.main import app
from app.schemas import (
    HumintFollowup,
    HumintGap,
    HumintInsight,
    HumintIirAnalysisResult,
    HumintIirParsedFields,
)


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def override_get_db(db_session: Session) -> Iterator[None]:
    def _get_db() -> Iterator[Session]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


class StubHumintIirAnalysisService:
    def __init__(self) -> None:
        self.calls: List[Tuple[int, int]] = []
        self.result = HumintIirAnalysisResult(
            mission_id=1,
            document_id=1,
            parsed_fields=HumintIirParsedFields(summary="SOURCE A REPORT"),
            key_insights=[
                HumintInsight(
                    title="Targets coordinating",
                    detail="SOURCE describes coordination in City X",
                    confidence=0.8,
                    supporting_evidence_ids=[1],
                )
            ],
            contradictions=["No corroboration"],
            gaps=[
                HumintGap(
                    title="Timing",
                    description="Need precise timing",
                    priority=2,
                    suggested_collection="OSINT",
                )
            ],
            followups=[
                HumintFollowup(
                    question="When is the meeting?",
                    rationale="Timing drives patrols",
                    priority=1,
                    related_gap_titles=["Timing"],
                    suggested_channel="source_debrief",
                )
            ],
            evidence_document_ids=[1],
            model_name="stub-model",
        )

    async def analyze_iir(self, mission_id: int, document_id: int) -> HumintIirAnalysisResult:
        self.calls.append((mission_id, document_id))
        return self.result


@pytest.fixture(autouse=True)
def override_humint_service(monkeypatch: pytest.MonkeyPatch) -> Iterator[StubHumintIirAnalysisService]:
    stub = StubHumintIirAnalysisService()

    async def _stub_factory(*args, **kwargs):  # pragma: no cover - FastAPI ignores async here
        return stub

    app.dependency_overrides[humint_api.get_humint_iir_analysis_service] = lambda: stub
    yield stub
    app.dependency_overrides.pop(humint_api.get_humint_iir_analysis_service, None)


def _create_mission_with_document(db: Session) -> Tuple[models.Mission, models.Document]:
    mission = models.Mission(name="Mission", mission_authority="LEO")
    db.add(mission)
    db.commit()
    db.refresh(mission)

    document = models.Document(mission_id=mission.id, title="IIR", content="UNCLASSIFIED text")
    db.add(document)
    db.commit()
    db.refresh(document)
    return mission, document


@pytest.mark.anyio
async def test_analyze_endpoint_returns_analysis_payload(
    client: httpx.AsyncClient,
    db_session: Session,
    override_humint_service: StubHumintIirAnalysisService,
) -> None:
    mission, document = _create_mission_with_document(db_session)

    response = await client.post(f"/missions/{mission.id}/humint/documents/{document.id}/analyze")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mission_id"] == mission.id
    assert payload["document_id"] == document.id
    assert "parsed_fields" in payload
    assert isinstance(payload["key_insights"], list)
    assert isinstance(payload["followups"], list)
    assert isinstance(payload["contradictions"], list)
    assert isinstance(payload["gaps"], list)
    assert isinstance(payload["evidence_document_ids"], list)

    assert override_humint_service.calls == [(mission.id, document.id)]
