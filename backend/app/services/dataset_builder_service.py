from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from app.config_aggregator import get_aggregator_config

logger = logging.getLogger(__name__)


class DatasetBuilderServiceError(Exception):
    """Raised when AggreGator profiling fails."""


class DatasetBuilderService:
    def __init__(self, *, timeout: float = 30.0) -> None:
        self._config = get_aggregator_config()
        self._timeout = timeout

    def build_dataset_profile(self, sources: List[Any]) -> Dict[str, Any]:
        """Call AggreGator /profile with the provided sources payload."""

        url = f"{self._config.base_url}/profile"
        payload = {"sources": sources}

        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("AggreGator profiling request failed")
            raise DatasetBuilderServiceError("AggreGator profiling request failed") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("AggreGator profiling response was not valid JSON")
            raise DatasetBuilderServiceError("Invalid AggreGator response format") from exc

        if not isinstance(data, dict):
            logger.error("AggreGator profile response must be a JSON object, got %s", type(data))
            raise DatasetBuilderServiceError("AggreGator profile response must be a JSON object")

        return data
