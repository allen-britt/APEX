from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AggreGatorConfig:
    base_url: str


_cached_config: AggreGatorConfig | None = None


def get_aggregator_config() -> AggreGatorConfig:
    global _cached_config
    if _cached_config is None:
        base_url = os.getenv("AGGREGATOR_BASE_URL", "http://localhost:8100").rstrip("/")
        if not base_url:
            raise ValueError("AGGREGATOR_BASE_URL cannot be empty")
        _cached_config = AggreGatorConfig(base_url=base_url)
    return _cached_config
