"""HUMINT IIR analysis service for DIA-style workflows (UNCLASSIFIED)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.humint.constants import DIA_HUMINT_PROFILE
from app.models.evidence import EvidenceBundle
from app.services import extraction_service as extraction_module
from app.services.evidence_extractor_service import EvidenceExtractorService
from app.services.llm_client import LLMCallException, LLMRole, call_llm_with_role, get_active_model

logger = logging.getLogger(__name__)


class ExtractionServiceProtocol:
    """Protocol-like base for extraction helpers leveraged by the HUMINT pipeline."""

    async def extract_entities_and_events_for_mission(  # pragma: no cover - protocol interface
        self,
        mission: models.Mission,
        documents: List[models.Document],
        profile: str = extraction_module.AnalysisProfile.HUMINT.value,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        raise NotImplementedError


class HumintIirAnalysisService:
    """Minimal DIA HUMINT IIR pipeline that returns structured analysis output."""

    def __init__(
        self,
        *,
        db: Session,
        extraction_service: Optional[ExtractionServiceProtocol] = None,
        evidence_extractor: Optional[EvidenceExtractorService] = None,
        llm_client: Any | None = None,
    ) -> None:
        self.db = db
        self._extraction_service = extraction_service or extraction_module
        self._evidence_extractor = evidence_extractor or EvidenceExtractorService(session=db)
        self._llm_override = llm_client

    async def analyze_iir(self, mission_id: int, document_id: int) -> schemas.HumintIirAnalysisResult:
        """Run the HUMINT IIR analysis workflow for the supplied mission/document."""

        mission = self._get_mission_or_404(mission_id)
        document = self._get_document_or_404(mission, document_id)

        iir_text = (document.content or "").strip()
        if not iir_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document has no textual content")

        entities, events = await self._extract_entities_and_events(mission, [document])
        evidence_bundle = self._build_evidence_bundle(mission.id)

        context_payload = self._build_analysis_context(
            mission,
            document,
            iir_text,
            entities,
            events,
            evidence_bundle,
        )
        llm_payload = await self._invoke_analysis_llm(context_payload)

        parsed_fields = schemas.HumintIirParsedFields(**llm_payload.get("parsed_fields", {}))
        key_insights = self._parse_insights(llm_payload.get("key_insights", []))
        contradictions = self._parse_contradictions(llm_payload.get("contradictions", []))
        gaps = self._parse_gaps(llm_payload.get("gaps", []))
        followups = self._parse_followups(llm_payload.get("followups", []))
        evidence_ids = self._collect_evidence_ids(document, key_insights, evidence_bundle)

        return schemas.HumintIirAnalysisResult(
            mission_id=mission.id,
            document_id=document.id,
            parsed_fields=parsed_fields,
            key_insights=key_insights,
            contradictions=contradictions,
            gaps=gaps,
            followups=followups,
            evidence_document_ids=sorted(evidence_ids),
            model_name=get_active_model(),
            run_id=None,
        )

    # ---------------------------------------------------------------------
    # Data access helpers
    # ---------------------------------------------------------------------

    def _get_mission_or_404(self, mission_id: int) -> models.Mission:
        mission = self.db.query(models.Mission).filter(models.Mission.id == mission_id).first()
        if not mission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
        return mission

    def _get_document_or_404(self, mission: models.Mission, document_id: int) -> models.Document:
        document = (
            self.db.query(models.Document)
            .filter(models.Document.id == document_id, models.Document.mission_id == mission.id)
            .first()
        )
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found for mission")
        return document

    # ---------------------------------------------------------------------
    # Extraction + evidence
    # ---------------------------------------------------------------------

    async def _extract_entities_and_events(
        self,
        mission: models.Mission,
        documents: List[models.Document],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        extractor = getattr(self._extraction_service, "extract_entities_and_events_for_mission", None)
        if extractor is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Extraction service unavailable")
        try:
            return await extractor(
                mission,
                documents,
                profile=extraction_module.AnalysisProfile.HUMINT.value,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Entity/event extraction failed")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Entity extraction failed") from exc

    def _build_evidence_bundle(self, mission_id: int) -> EvidenceBundle | None:
        try:
            return self._evidence_extractor.build_evidence_bundle(mission_id)
        except Exception:
            logger.info("Evidence bundle unavailable for mission %s", mission_id, exc_info=True)
            return None

    # ---------------------------------------------------------------------
    # Context + LLM call
    # ---------------------------------------------------------------------

    def _build_analysis_context(
        self,
        mission: models.Mission,
        document: models.Document,
        iir_text: str,
        entities: Sequence[Dict[str, Any]],
        events: Sequence[Dict[str, Any]],
        bundle: EvidenceBundle | None,
    ) -> Dict[str, Any]:
        return {
            "profile": DIA_HUMINT_PROFILE,
            "mission": {
                "id": mission.id,
                "name": mission.name,
                "description": mission.description,
                "authority": mission.mission_authority,
                "int_lanes": list(mission.int_types or []),
            },
            "document": {
                "id": document.id,
                "title": document.title,
                "created_at": document.created_at.isoformat() if getattr(document, "created_at", None) else None,
            },
            "iir_text": iir_text,
            "extracted_entities": list(entities),
            "extracted_events": list(events),
            "evidence_summary": self._summarize_evidence(bundle),
        }

    def _summarize_evidence(self, bundle: EvidenceBundle | None) -> Dict[str, Any]:
        if not bundle:
            return {"has_snapshot": False}
        return {
            "has_snapshot": True,
            "incident_count": len(bundle.incidents),
            "subject_count": len(bundle.subjects),
            "document_ids": [doc.id for doc in bundle.documents],
            "kg_summary": bundle.kg_snapshot_summary,
        }

    async def _invoke_analysis_llm(self, context_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = (
            "You are a DIA HUMINT analyst producing an UNCLASSIFIED structured assessment of an IIR. "
            "Return ONLY JSON matching the requested schema."
        )
        user_prompt = (
            "Context JSON:\n"
            f"{json.dumps(context_payload, ensure_ascii=False, indent=2)}\n\n"
            "Respond with JSON using this template:\n"
            "{\n"
            "  \"parsed_fields\": {...},\n"
            "  \"key_insights\": [{\"title\": str, \"detail\": str, \"confidence\": float, \"supporting_evidence_ids\": [int]}],\n"
            "  \"contradictions\": [str],\n"
            "  \"gaps\": [{\"title\": str, \"description\": str, \"priority\": int, \"suggested_collection\": str|null}],\n"
            "  \"followups\": [{\"question\": str, \"rationale\": str, \"priority\": int, \"related_gap_titles\": [str], \"suggested_channel\": str|null}]\n"
            "}\n"
            "All language must remain UNCLASSIFIED / training safe."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        override = self._llm_override
        if override is not None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            raw_response = override.chat(messages)
            return json.loads(raw_response)

        try:
            raw_response = await call_llm_with_role(
                prompt=user_prompt,
                system=system_prompt,
                role=LLMRole.ANALYSIS_PRIMARY,
            )
        except LLMCallException as exc:  # pragma: no cover - network failure
            logger.exception("LLM analysis call failed")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM analysis failed") from exc
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned invalid JSON: %s", raw_response)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM returned invalid JSON") from exc

    # ---------------------------------------------------------------------
    # Parsing helpers
    # ---------------------------------------------------------------------

    def _parse_insights(self, items: Sequence[Dict[str, Any]]) -> List[schemas.HumintInsight]:
        insights: List[schemas.HumintInsight] = []
        for item in items:
            title = (item or {}).get("title")
            detail = (item or {}).get("detail")
            if not title or not detail:
                continue
            confidence = self._coerce_float(item.get("confidence"), default=0.5)
            confidence = min(max(confidence, 0.0), 1.0)
            supporting_ids = self._coerce_int_list(item.get("supporting_evidence_ids", []))
            insights.append(
                schemas.HumintInsight(
                    title=str(title),
                    detail=str(detail),
                    confidence=confidence,
                    supporting_evidence_ids=supporting_ids,
                )
            )
        return insights

    def _parse_contradictions(self, values: Sequence[Any]) -> List[str]:
        return [str(value).strip() for value in values if str(value).strip()]

    def _parse_gaps(self, items: Sequence[Dict[str, Any]]) -> List[schemas.HumintGap]:
        gaps: List[schemas.HumintGap] = []
        for item in items:
            title = (item or {}).get("title")
            description = (item or {}).get("description")
            if not title or not description:
                continue
            priority = self._coerce_int(item.get("priority"), default=3)
            priority = min(max(priority, 1), 3)
            gaps.append(
                schemas.HumintGap(
                    title=str(title),
                    description=str(description),
                    priority=priority,
                    suggested_collection=item.get("suggested_collection"),
                )
            )
        return gaps

    def _parse_followups(self, items: Sequence[Dict[str, Any]]) -> List[schemas.HumintFollowup]:
        followups: List[schemas.HumintFollowup] = []
        for item in items:
            question = (item or {}).get("question")
            rationale = (item or {}).get("rationale")
            if not question or not rationale:
                continue
            priority = self._coerce_int(item.get("priority"), default=3)
            priority = min(max(priority, 1), 3)
            followups.append(
                schemas.HumintFollowup(
                    question=str(question),
                    rationale=str(rationale),
                    priority=priority,
                    related_gap_titles=[
                        str(val).strip() for val in item.get("related_gap_titles", []) if str(val).strip()
                    ],
                    suggested_channel=item.get("suggested_channel"),
                )
            )
        return followups

    def _collect_evidence_ids(
        self,
        document: models.Document,
        insights: Sequence[schemas.HumintInsight],
        bundle: EvidenceBundle | None,
    ) -> Set[int]:
        evidence_ids: Set[int] = {document.id}
        for insight in insights:
            for value in insight.supporting_evidence_ids:
                evidence_ids.add(value)
        if bundle:
            for doc in bundle.documents:
                converted = self._coerce_int(doc.id, default=None)
                if converted is not None:
                    evidence_ids.add(converted)
        return evidence_ids

    # ---------------------------------------------------------------------
    # Coercion helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _coerce_float(value: Any, *, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_int(value: Any, *, default: int | None) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _coerce_int_list(self, values: Sequence[Any]) -> List[int]:
        result: List[int] = []
        for value in values:
            converted = self._coerce_int(value, default=None)
            if converted is not None:
                result.append(converted)
        return result
