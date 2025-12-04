from __future__ import annotations

from datetime import datetime
from collections.abc import Mapping
from typing import Any, Dict, List, Sequence

from app import models
from app.policy_authorities import authority_id_to_label, normalize_authority_id


def _isoformat_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def build_authority_history_entries(mission: models.Mission | Mapping[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(mission, Mapping):
        raw_entries = mission.get("authority_history")
        if isinstance(raw_entries, list):
            normalized: List[Dict[str, Any]] = []
            for entry in raw_entries:
                if isinstance(entry, Mapping):
                    normalized.append(
                        {
                            "type": entry.get("type"),
                            "from": entry.get("from"),
                            "to": entry.get("to"),
                            "justification": entry.get("justification"),
                            "actor": entry.get("actor"),
                            "risk": entry.get("risk"),
                            "conditions": list(entry.get("conditions") or []),
                            "created_at": entry.get("created_at"),
                        }
                    )
            if normalized:
                return normalized
        # fall back to minimal original entry if mission metadata present
        original_auth = mission.get("original_authority") or mission.get("mission_authority")
        created_at = mission.get("created_at")
        if original_auth:
            return [
                {
                    "type": "original",
                    "from": None,
                    "to": original_auth,
                    "justification": None,
                    "actor": None,
                    "risk": None,
                    "conditions": [],
                    "created_at": created_at,
                }
            ]
        return []

    entries: List[Dict[str, Any]] = [
        {
            "type": "original",
            "from": None,
            "to": mission.original_authority,
            "justification": None,
            "actor": None,
            "risk": None,
            "conditions": [],
            "created_at": _isoformat_or_none(mission.created_at),
        }
    ]

    for pivot in mission.authority_pivots or []:
        entries.append(
            {
                "type": "pivot",
                "from": pivot.from_authority,
                "to": pivot.to_authority,
                "justification": pivot.justification,
                "actor": pivot.actor,
                "risk": pivot.risk,
                "conditions": list(pivot.conditions or []),
                "created_at": _isoformat_or_none(pivot.created_at),
            }
        )

    return entries


def _describe_authority(value: str | None) -> str:
    normalized = normalize_authority_id(value) if value else None
    if normalized:
        return authority_id_to_label(normalized)
    return value or "Unknown authority"


def render_authority_history_lines(entries: Sequence[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for entry in entries:
        timestamp = entry.get("created_at") or "unspecified"
        entry_type = entry.get("type")
        if entry_type == "original":
            to_label = _describe_authority(entry.get("to"))
            lines.append(f"- [{timestamp}] Original authority established as {to_label}.")
            continue

        from_label = _describe_authority(entry.get("from"))
        to_label = _describe_authority(entry.get("to"))
        risk = entry.get("risk") or "N/A"
        conditions = entry.get("conditions") or []
        conditions_note = ""
        if conditions:
            joined = "; ".join(str(cond) for cond in conditions if str(cond).strip())
            if joined:
                conditions_note = f" | Conditions: {joined}"
        lines.append(
            f"- [{timestamp}] Pivot: {from_label} → {to_label} | Risk: {risk}{conditions_note}"
        )
    return lines


def build_authority_history_payload(mission: models.Mission) -> Dict[str, Any]:
    entries = build_authority_history_entries(mission)
    return {
        "entries": entries,
        "lines": render_authority_history_lines(entries),
    }
