from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from app.config_aggregator import get_aggregator_config

logger = logging.getLogger(__name__)


class KgClientError(Exception):
    """Raised when AggreGator KG requests fail."""


class KgClient:
    """Small wrapper around AggreGator graph endpoints for APEX services."""

    def __init__(self, *, timeout: float = 10.0) -> None:
        self._cfg = get_aggregator_config()
        self._timeout = timeout

    @staticmethod
    def project_id_from_mission(mission_id: int) -> str:
        """Derive AggreGator project_id for the given mission.

        For now we use a simple naming convention; this can evolve once a
        true linkage between missions and aggregator projects exists.
        """

        return f"mission-{mission_id}"

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self._cfg.base_url}{path}"
        try:
            response = httpx.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("KG request failed: %s", url)
            raise KgClientError("AggreGator KG request failed") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("KG response was not valid JSON for %s", url)
            raise KgClientError("AggreGator KG response was not valid JSON") from exc

        if not isinstance(data, dict):
            raise KgClientError("AggreGator KG response must be a JSON object")

        return data

    def get_summary(self, project_id: str) -> Dict[str, Any]:
        """Return overall node/edge counts and top labels for a project."""

        return self._request("/graph/summary", params={"project_id": project_id})

    def get_full_graph(
        self,
        project_id: str,
        *,
        limit_nodes: int = 400,
        limit_edges: int = 800,
    ) -> Dict[str, Any]:
        """Fetch sampled nodes/edges for visualization or analysis."""

        params = {
            "project_id": project_id,
            "limit_nodes": limit_nodes,
            "limit_edges": limit_edges,
        }
        return self._request("/graph/all", params=params)

    def get_neighborhood(self, project_id: str, node_id: str, *, hops: int = 2) -> Dict[str, Any]:
        """Fetch a node-centric neighborhood view from the KG."""

        params = {"project_id": project_id, "node_id": node_id, "hops": hops}
        return self._request("/graph/neighborhood", params=params)

    def get_suggested_links(self, project_id: str, *, limit: int = 50) -> Dict[str, Any]:
        """Return link suggestions AggreGator can provide for the project."""

        params = {"project_id": project_id, "limit": limit}
        return self._request("/graph/suggest-links", params=params)

    def get_network_metrics(self, project_id: str) -> Dict[str, Any]:
        """Alias for get_summary so callers can focus on semantics."""

        return self.get_summary(project_id)
