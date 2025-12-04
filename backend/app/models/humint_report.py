from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class HumintReport(Base):
    __tablename__ = "humint_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_id: Mapped[str]
    raw_text: Mapped[str]
    structured_sections: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    mission_id: Mapped[Optional[int]] = mapped_column(ForeignKey("missions.id"), nullable=True)
    mission = relationship("Mission", back_populates="humint_reports")

    insights = relationship(
        "HumintInsight",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    follow_up_plan = relationship(
        "HumintFollowUpPlan",
        back_populates="report",
        cascade="all, delete-orphan",
        uselist=False,
    )
