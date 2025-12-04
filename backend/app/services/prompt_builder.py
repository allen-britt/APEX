from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Sequence

from app.services.authority_history import (
    build_authority_history_entries,
    render_authority_history_lines,
)
from app.services.kg_snapshot_utils import summarize_kg_metrics
from app.services.policy_context import build_policy_prompt


def _extract_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _resolve_mission_block(context: Mapping[str, Any]) -> Mapping[str, Any]:
    mission_block = context.get("mission")
    if isinstance(mission_block, Mapping):
        return mission_block
    return context


def _extract_authority(context: Mapping[str, Any]) -> tuple[str | None, Sequence[str]]:
    mission_block = _resolve_mission_block(context)
    authority = (
        context.get("authority")
        or context.get("mission_authority")
        or mission_block.get("mission_authority")
    )
    int_codes = (
        context.get("int_types")
        or context.get("ints")
        or mission_block.get("int_types")
        or context.get("mission", {}).get("int_types")
        or []
    )
    if isinstance(int_codes, Sequence):
        return authority, int_codes
    return authority, []


def build_global_system_prompt(
    mission_context: Mapping[str, Any],
    task_instructions: str,
) -> str:
    """Compose a unified system prompt with policy, history, and KG summary."""

    context = _extract_mapping(mission_context)
    mission_block = _resolve_mission_block(context)

    authority, int_codes = _extract_authority(context)

    history_entries = build_authority_history_entries(mission_block)
    history_lines = render_authority_history_lines(history_entries)
    if not history_lines:
        history_lines = ["- No authority pivots recorded for this mission."]

    policy_block = build_policy_prompt(authority, int_codes)

    kg_summary = context.get("kg_summary")
    if kg_summary is None:
        kg_summary = mission_block.get("kg_summary")
    kg_block = "Knowledge Graph Summary:\n" + summarize_kg_metrics(kg_summary)

    history_block = "Authority History:\n" + "\n".join(history_lines)

    instructions_block = task_instructions.strip()

    sections = [policy_block, history_block, kg_block, instructions_block]
    return "\n\n".join(section for section in sections if section)
