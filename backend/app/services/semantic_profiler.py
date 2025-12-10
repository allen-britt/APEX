from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from app.models import MissionDataset
from app.services.llm_client import LLMCallException, LLMRole, call_llm_with_role

logger = logging.getLogger(__name__)


SEMANTIC_ANNOTATOR_SYSTEM_PROMPT = (
    "You are a data semantics analyst supporting Project APEX. "
    "Given a mission dataset profile (tables and columns), infer the semantic purpose of each column. "
    "Respond ONLY with valid JSON using the schema: {\"columns\": [{\"name\": str, \"semantic_type\": str, \"confidence\": float, \"role\": str, \"notes\": str}]}. "
    "Confidence must be between 0 and 1. Keep notes short and actionable."
)


class SemanticProfilerError(Exception):
    """Raised when semantic profiling fails."""


class SemanticProfiler:
    def __init__(self, *, timeout: float = 20.0) -> None:
        self._timeout = timeout

    def _build_prompt(self, dataset: MissionDataset) -> str:
        profile_json = json.dumps(dataset.profile or {}, ensure_ascii=False, indent=2)
        return (
            f"Dataset name: {dataset.name}\n"
            "Mission dataset profile JSON:\n"
            f"{profile_json}\n"
            "Provide the semantic annotation JSON as specified."
        )

    def generate(self, dataset: MissionDataset, *, policy_block: str | None = None) -> Dict[str, Any]:
        if not dataset.profile:
            raise SemanticProfilerError("Dataset has no profile to analyze")

        prompt = self._build_prompt(dataset)

        async def _call() -> str:
            return await call_llm_with_role(
                prompt=prompt,
                system=SEMANTIC_ANNOTATOR_SYSTEM_PROMPT,
                policy_block=policy_block,
                role=LLMRole.UTILITY_FAST,
            )

        try:
            response = asyncio.run(_call())
        except LLMCallException as exc:
            raise SemanticProfilerError("LLM semantic profiling failed") from exc

        try:
            data = json.loads(response)
        except json.JSONDecodeError as exc:
            logger.exception("Semantic profiler returned invalid JSON: %s", response)
            raise SemanticProfilerError("Semantic profiler returned invalid JSON") from exc

        columns = data.get("columns") if isinstance(data, dict) else None
        if not isinstance(columns, list):
            logger.error("Semantic profiler response missing 'columns': %s", data)
            raise SemanticProfilerError("Semantic profiler response missing 'columns'")

        return data
