from __future__ import annotations

from typing import Iterable, List, Protocol, Sequence

from app import models


class TemplateMetadata(Protocol):
    mission_domains: Sequence[str]
    title10_allowed: bool
    title50_allowed: bool
    allowed_authorities: Sequence[str]
    allowed_int_types: Sequence[str]
    int_types: Sequence[str]


def filter_templates_for_mission(
    *, mission: models.Mission, templates: Iterable[TemplateMetadata]
) -> List[TemplateMetadata]:
    authority_value = (
        (mission.mission_authority or getattr(mission, "original_authority", None) or "")
        .strip()
        .upper()
    )
    authority = authority_value or None
    mission_ints = {value.strip().upper() for value in (mission.int_types or []) if value}

    def _is_authority_allowed(tpl: TemplateMetadata) -> bool:
        if not tpl.allowed_authorities:
            return True
        if authority is None:
            return False
        return authority in tpl.allowed_authorities

    def _is_int_allowed(tpl: TemplateMetadata) -> bool:
        if not mission_ints:
            return True
        template_ints = {
            value.strip().upper()
            for value in (getattr(tpl, "int_types", None) or getattr(tpl, "allowed_int_types", []) or [])
            if value
        }
        if not template_ints:
            return True
        return not mission_ints.isdisjoint(template_ints)

    return [tpl for tpl in templates if _is_authority_allowed(tpl) and _is_int_allowed(tpl)]
