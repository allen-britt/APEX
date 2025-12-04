from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app import models
from app.services.aggregator_client import AggregatorClient, AggregatorClientError


logger = logging.getLogger(__name__)
_aggregator_client = AggregatorClient()


def ensure_mission_namespace(
    mission: models.Mission,
    *,
    db: Optional[Session] = None,
) -> str:
    """Ensure the AggreGator namespace for this mission exists and is initialized."""

    namespace = mission.kg_namespace or f"mission-{mission.id}"

    if mission.kg_namespace != namespace:
        mission.kg_namespace = namespace
        if db is not None:
            db.add(mission)
            db.commit()
            db.refresh(mission)

    try:
        _aggregator_client.init_namespace(namespace)
    except AggregatorClientError:
        logger.warning(
            "Failed to initialize AggreGator namespace for mission %s (namespace=%s)",
            mission.id,
            namespace,
            exc_info=True,
        )

    return namespace
