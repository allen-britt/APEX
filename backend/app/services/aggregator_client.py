from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config_aggregator import get_aggregator_config

logger = logging.getLogger(__name__)


class AggregatorClientError(Exception):
    """Raised when AggreGator namespace operations fail."""


class AggregatorClient:
    def __init__(self, *, timeout: float = 5.0) -> None:
        self._cfg = get_aggregator_config()
        self._timeout = timeout

    def init_namespace(self, namespace: str) -> None:
        """Ensure the given namespace exists in AggreGator."""

        url = f"{self._cfg.base_url}/kg/namespaces"
        payload: dict[str, Any] = {"namespace": namespace}

        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
        except httpx.HTTPError as exc:
            logger.exception("AggreGator namespace init request failed")
            raise AggregatorClientError("Failed to initialize AggreGator namespace") from exc

        if response.status_code in (200, 201, 204, 409):
            return

        logger.warning(
            "AggreGator namespace init returned unexpected status %s", response.status_code
        )
        raise AggregatorClientError("AggreGator namespace init returned non-success status")

    def ingest_document(
        self,
        namespace: str,
        *,
        title: str | None,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._cfg.base_url}/kg/{namespace}/documents"
        payload: dict[str, Any] = {
            "namespace": namespace,
            "title": title or "Mission Document",
            "text": text,
            "metadata": metadata or {},
        }

        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("AggreGator document ingest failed for namespace %s", namespace)
            raise AggregatorClientError("AggreGator document ingest failed") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("AggreGator document ingest returned invalid JSON")
            raise AggregatorClientError("AggreGator ingest response invalid") from exc

        if not isinstance(data, dict):
            raise AggregatorClientError("AggreGator ingest response must be an object")

        return data

    def get_graph_summary(self, namespace: str) -> dict[str, Any]:
        url = f"{self._cfg.base_url}/graph/summary"
        params = {"project_id": namespace}

        try:
            response = httpx.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("AggreGator graph summary failed for namespace %s", namespace)
            raise AggregatorClientError("AggreGator graph summary failed") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("AggreGator graph summary returned invalid JSON")
            raise AggregatorClientError("AggreGator graph summary invalid response") from exc

        if not isinstance(data, dict):
            raise AggregatorClientError("AggreGator graph summary must return an object")

        return data

    def ingest_json_payload(
        self,
        namespace: str,
        *,
        title: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Helper that serializes structured payloads before ingestion."""

        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return self.ingest_document(
            namespace,
            title=title,
            text=text,
            metadata=metadata,
        )

    def get_mission_kg_snapshot(
        self,
        namespace: str,
        *,
        authority: str,
        int_types: list[str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._cfg.base_url}/kg/{namespace}/snapshot"
        payload: dict[str, Any] = {
            "namespace": namespace,
            "mission_authority": authority,
            "int_types": int_types or [],
        }

        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("AggreGator KG snapshot request failed for namespace %s", namespace)
            raise AggregatorClientError("Failed to fetch mission KG snapshot") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("AggreGator KG snapshot returned invalid JSON")
            raise AggregatorClientError("AggreGator KG snapshot response invalid") from exc

        if not isinstance(data, dict):
            raise AggregatorClientError("AggreGator KG snapshot response must be an object")

        return data
