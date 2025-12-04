from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence

from app.services import llm_client
from app.services.policy_context import guardrail_keyword_hits

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


def run_guardrails(
    summary: str,
    next_steps: str,
    *,
    authority: str | None = None,
    authority_history: Sequence[str] | None = None,
    authority_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
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

    policy_hits = guardrail_keyword_hits(authority, f"{summary_text}\n{next_steps_text}") if authority else []
    if policy_hits:
        issues.extend(policy_hits)
        status = "blocked"

    if issues and status != "blocked":
        status = "warning"

    metadata = authority_metadata or {}
    result: Dict[str, Any] = {
        "status": status,
        "issues": issues,
        "original_authority": metadata.get("original_authority"),
        "current_authority": metadata.get("current_authority", authority),
        "has_pivots": metadata.get("has_pivots", bool(authority_history)),
    }
    if authority_history:
        result["authority_history"] = list(authority_history)
    return result


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
    authority: str | None = None,
    policy_block: str | None = None,
    authority_history: Sequence[str] | None = None,
    authority_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
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
            policy_block=policy_block,
        )
    except Exception:
        review = {"status": "REVIEW", "issues": ["Guardrail LLM review failed; manual inspection required."]}

    review_status = (review.get("status") or "REVIEW").upper()
    review_score = STATUS_LEVELS.get(review_status, STATUS_LEVELS["REVIEW"])
    review_issues = _list_from_mapping(review, "issues")
    if review_issues:
        issues.extend(review_issues)
    score = max(score, review_score)

    policy_hits = guardrail_keyword_hits(authority, summary) if authority else []
    policy_hits += guardrail_keyword_hits(authority, estimate) if authority else []
    if policy_hits:
        issues.extend(policy_hits)
        score = max(score, STATUS_LEVELS["REVIEW"])

    final_status = next((name for name, level in STATUS_LEVELS.items() if level == score), "REVIEW")
    metadata = authority_metadata or {}
    return {
        "status": final_status,
        "issues": issues,
        "original_authority": metadata.get("original_authority"),
        "current_authority": metadata.get("current_authority", authority),
        "has_pivots": metadata.get("has_pivots", bool(authority_history)),
        "authority_history": list(authority_history or []),
    }
