from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Sequence, Tuple

from app.services import llm_client

BANNED_WORDS = ["kill", "classified", "US PERSON", "lethal"]
ISO_TIMESTAMP_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"
)

_HAS_DOCS_CONTEXT = True


def set_guardrail_context(*, has_docs: bool) -> None:
    """Configure contextual information for the next guardrail run."""

    global _HAS_DOCS_CONTEXT
    _HAS_DOCS_CONTEXT = has_docs


def _find_future_timestamps(text: str) -> List[str]:
    future_markers: List[str] = []
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(days=1)

    for match in ISO_TIMESTAMP_PATTERN.findall(text):
        candidate = match.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        if parsed > threshold:
            future_markers.append(match)

    return future_markers


def run_guardrails(summary: str, next_steps: str) -> Dict[str, List[str]]:
    """Evaluate generated content for safety and policy adherence."""

    issues: List[str] = []
    status = "ok"

    summary_text = (summary or "").strip()
    next_steps_text = (next_steps or "").strip()
    combined_text = f"{summary_text}\n{next_steps_text}".lower()

    banned_hits = [word for word in BANNED_WORDS if word.lower() in combined_text]
    if banned_hits:
        issues.append(
            "Detected banned terminology: " + ", ".join(sorted(set(banned_hits)))
        )
        status = "blocked"

    future_markers = _find_future_timestamps(f"{summary_text}\n{next_steps_text}")
    if future_markers:
        issues.append(
            "References timestamps too far in the future: " + ", ".join(future_markers)
        )
        status = "blocked"

    if not summary_text:
        issues.append("Summary is empty.")
    if not next_steps_text:
        issues.append("Next steps are empty.")

    if "source:" in combined_text and not _HAS_DOCS_CONTEXT:
        issues.append("Mentions a source despite no mission documents being available.")
        status = "blocked"

    if issues and status != "blocked":
        status = "warning"

    return {"status": status, "issues": issues}


STATUS_LEVELS = {"OK": 0, "CAUTION": 1, "REVIEW": 2}


def _normalize_gap_entries(gaps: Dict | List | None) -> List[dict]:
    if isinstance(gaps, dict):
        items = gaps.get("gaps", [])
    else:
        items = gaps or []
    return [item for item in items if isinstance(item, dict)]


def _list_from_mapping(data: Dict, key: str) -> List[str]:
    value = data.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


async def evaluate_guardrails(
    *,
    facts: Sequence[dict],
    entities: Sequence[dict],
    events: Sequence[dict],
    estimate: str,
    summary: str,
    gaps: Dict | List | None,
    cross: Dict,
    profile: str = "humint",
) -> Tuple[str, List[str]]:
    """Score analytic quality using heuristics plus LLM validation."""

    issues: List[str] = []
    score = 0

    def flag(level: int, message: str) -> None:
        nonlocal score
        if message:
            issues.append(message)
        score = max(score, level)

    if not facts:
        flag(1, "No raw facts extracted; collection may be insufficient.")

    if not entities:
        flag(1, "Entity list is empty.")

    if not events:
        flag(1, "Event list is empty.")
    else:
        timestamps = [event.get("timestamp") for event in events if isinstance(event, dict)]
        if timestamps and all(ts is None for ts in timestamps):
            flag(1, "All events are missing timestamps.")

    if not (estimate or "").strip():
        flag(1, "Operational estimate is empty.")

    if not (summary or "").strip():
        flag(1, "Summary is empty.")

    gap_entries = _normalize_gap_entries(gaps)
    high_priority = sum(1 for gap in gap_entries if (gap.get("priority") or "").lower() == "high")
    if high_priority:
        flag(1, f"{high_priority} high-priority information gaps remain unresolved.")

    contradictions = _list_from_mapping(cross or {}, "contradictions")
    if contradictions:
        flag(1, "Cross-document contradictions detected.")

    try:
        review = await llm_client.guardrail_quality_review(
            summary=summary,
            estimate=estimate,
            gaps=gaps or {"gaps": gap_entries},
            cross=cross or {},
            profile=profile,
        )
    except Exception:
        review = {"status": "REVIEW", "issues": ["Guardrail LLM review failed; manual inspection required."]}

    review_status = (review.get("status") or "REVIEW").upper()
    review_score = STATUS_LEVELS.get(review_status, STATUS_LEVELS["REVIEW"])
    review_issues = _list_from_mapping(review, "issues")
    if review_issues:
        issues.extend(review_issues)
    score = max(score, review_score)

    final_status = next((name for name, level in STATUS_LEVELS.items() if level == score), "REVIEW")
    return final_status, issues
