from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.db.session import Base, engine
from app import models  # noqa: F401
from app.authorities import AuthorityType


logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create database tables, tolerating concurrent initialization."""

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        message = str(getattr(exc, "orig", exc)).lower()
        if "already exists" in message:
            logger.debug("Database tables already exist; skipping create_all", exc_info=False)
        else:
            raise

    _ensure_original_authority_column()


def _ensure_original_authority_column() -> None:
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("missions")}
    if "original_authority" in columns:
        return

    logger.info("Adding original_authority column to missions table")
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE missions ADD COLUMN original_authority VARCHAR NOT NULL DEFAULT 'LEO'"
            ),
        )
        conn.execute(
            text(
                "UPDATE missions SET original_authority = mission_authority WHERE original_authority IS NULL OR original_authority = ''"
            )
        )
