from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple

from app import models
from app.models import Document
from app.services import llm_client
from app.services.authority_history import build_authority_history_payload
from app.services.policy_context import build_policy_prompt


class AnalysisProfile(str, Enum):
    HUMINT = "humint"
    SIGINT = "sigint"
    OSINT = "osint"


PROFILE_NOTES = {
    AnalysisProfile.HUMINT: "Focus on people, groups, intent, relationships, and locations.",
    AnalysisProfile.SIGINT: "Focus on technical systems, communications, platforms, frequencies, and networks.",
    AnalysisProfile.OSINT: "Focus on public indicators, media, organizations, infrastructure, and overt signals.",
}


def _profile_note(profile: AnalysisProfile) -> str:
    return PROFILE_NOTES.get(profile, PROFILE_NOTES[AnalysisProfile.HUMINT])


def _build_context(
    mission: models.Mission,
    documents: List[Document],
    profile: AnalysisProfile,
) -> str:
    sections: List[str] = []

    filtered_documents = [
        doc for doc in documents if getattr(doc, "include_in_analysis", True)
    ]

    mission_header = [f"Mission: {mission.name}"]
    if mission.description:
        mission_header.append(f"Description: {mission.description.strip()}")
    mission_header.append(f"Analysis profile: {profile.value.upper()} - {_profile_note(profile)}")
    sections.append("\n".join(mission_header))

    for idx, doc in enumerate(filtered_documents, start=1):
        doc_lines = [f"Document {idx}:"]
        if getattr(doc, "title", None):
            doc_lines.append(f"Title: {doc.title}")
        if getattr(doc, "created_at", None):
            doc_lines.append(f"Timestamp: {doc.created_at.isoformat()}")
        content = (doc.content or "").strip()
        if content:
            doc_lines.append("Content:")
            doc_lines.append(content)
        sections.append("\n".join(doc_lines))

    return "\n\n".join(section for section in sections if section.strip())


def _dedupe_entities(entities: List[Dict]) -> List[Dict]:
    deduped: Dict[str, Dict] = {}
    for entity in entities:
        key = entity.get("name", "").strip().lower()
        if not key:
            continue
        if key not in deduped:
            deduped[key] = entity
    return list(deduped.values())


async def extract_entities_and_events_for_mission(
    mission: models.Mission,
    documents: List[Document],
    profile: str = AnalysisProfile.HUMINT.value,
) -> Tuple[List[Dict], List[Dict]]:
    """Return structured entities and events for a mission using the selected profile."""

    try:
        profile_enum = AnalysisProfile(profile)
    except ValueError:
        profile_enum = AnalysisProfile.HUMINT

    authority_history = build_authority_history_payload(mission)
    context = _build_context(mission, documents, profile_enum)
    if not context:
        return [], []

    policy_block = build_policy_prompt(
        mission.mission_authority,
        mission.int_types,
        authority_history=authority_history["lines"],
    )
    entities = await llm_client.extract_entities(
        context,
        profile=profile_enum.value,
        policy_block=policy_block,
    )
    events = await llm_client.extract_events(
        context,
        profile=profile_enum.value,
        policy_block=policy_block,
    )

    return _dedupe_entities(entities), events
