"""Helpers for composing authority/INT policy prompts and enforcing guardrails."""

from __future__ import annotations

from typing import List, Sequence

from app.authorities import (
    AuthorityDescriptor,
    AuthorityType,
    authority_prompt_block,
    get_descriptor,
    normalize_authority,
    try_get_descriptor,
)
from app.config.int_registry import IntMetadata, get_int_registry

# Cache INT metadata for quick lookups
_INT_METADATA_MAP = {meta.code.upper(): meta for meta in get_int_registry()}


def _normalize_int_codes(int_codes: Sequence[str] | None) -> List[str]:
    """Return uppercase, stripped INT codes, skipping falsy entries."""
    if not int_codes:
        return []
    normalized: List[str] = []
    for code in int_codes:
        if not code:
            continue
        upper = str(code).strip().upper()
        if upper:
            normalized.append(upper)
    return normalized


def _format_int_sensitivity_lines(int_codes: List[str]) -> str:
    """Format INT sensitivity notes for inclusion in prompts."""
    if not int_codes:
        return (
            "- Default OSINT posture: rely on publicly releasable information unless "
            "specific INT authorizations are granted."
        )

    lines: List[str] = []
    for code in int_codes:
        metadata: IntMetadata | None = _INT_METADATA_MAP.get(code)
        if metadata:
            lines.append(f"- {metadata.label}: {metadata.legal_sensitivity_notes}")
        else:
            lines.append(
                f"- {code}: Handle using standard minimization and legal review procedures."
            )
    return "\n".join(lines)


def build_policy_prompt(
    authority: str | AuthorityType | None,
    int_codes: Sequence[str] | None,
    *,
    authority_history: Sequence[str] | None = None,
) -> str:
    """
    Produce a reusable policy block covering:
      - Authority lane summary, do/dont notes, and examples
      - Selected INT sensitivity guidance
      - Compliance reminder that hard boundaries override creativity
    """
    descriptor = try_get_descriptor(authority)
    if descriptor:
        authority_block = authority_prompt_block(descriptor.value)
        lane_label = descriptor.label
    else:
        lane_label = "the current mission lane"
        authority_block = (
            "Authority Lane: Unspecified or Missing\n"
            "Context: Mission metadata did not specify an authority lane. Keep analysis within documented mission scope and do not assume criminal, military, or intelligence authorities.\n"
            "Prohibitions: Decline any recommendation that would require unverified legal powers or law-enforcement actions."
        )

    normalized_ints = _normalize_int_codes(int_codes)
    int_lines = _format_int_sensitivity_lines(normalized_ints)
    ints_section = "INT Sensitivity Notes:\n" + int_lines

    history_section = ""
    if authority_history:
        history_body = "\n".join(str(line) for line in authority_history if str(line).strip())
        if history_body:
            history_section = f"Authority History:\n{history_body}\n\n"

    closing = (
        "Compliance Reminder: Hard boundaries override creativity. If any request conflicts with "
        f"{lane_label} guidance or the approved INT set "
        f"({', '.join(normalized_ints) if normalized_ints else 'OSINT defaults'}), "
        "the assistant must refuse and issue a policy warning. When authority pivots occur, the assistant must "
        "respect the current authority AND explicitly honor any risks or conditions documented in the pivot history."
    )

    return f"{authority_block}\n\n{history_section}{ints_section}\n\n{closing}"


def find_disallowed_ints(
    authority: str | AuthorityType | None,
    mission_ints: Sequence[str] | None,
) -> List[str]:
    """Return human-readable issues for INT selections not permitted under the authority."""
    descriptor = try_get_descriptor(authority)
    if descriptor is None:
        return []
    allowed = {code.upper() for code in descriptor.allowed_int_types} if descriptor.allowed_int_types else set()
    if not allowed or not mission_ints:
        return []

    issues: List[str] = []
    for code in mission_ints:
        upper = str(code or "").strip().upper()
        if not upper or upper in allowed:
            continue
        issues.append(
            f"INT {upper} is not authorized under the {descriptor.label} lane. "
            "Remove it or change the mission authority."
        )
    return issues


def guardrail_keyword_hits(
    authority: str | AuthorityType | None,
    text: str,
) -> List[str]:
    """Return guardrail issues if authority-specific forbidden keywords appear in the text."""
    if not text:
        return []

    descriptor = try_get_descriptor(authority)
    if descriptor is None:
        return ["Note: Some requested content exceeded the mission's specified authority lane. The response has been limited accordingly."]
    lowered = text.lower()
    hits: List[str] = []

    for keyword in descriptor.guardrail_keywords:
        if keyword.lower() in lowered:
            hits.append(keyword)

    if not hits:
        return []

    return [
        "Detected out-of-lane request referencing disallowed terms for "
        f"{descriptor.label}: {', '.join(sorted(set(hits)))}"
    ]
