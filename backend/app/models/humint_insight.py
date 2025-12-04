# backend/app/models/humint_insight.py

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Float, String, JSON, ForeignKey
from app.db.session import Base


class HumintInsight(Base):
    __tablename__ = "humint_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("humint_reports.id"), index=True)

    description: Mapped[str] = mapped_column(String)

    novelty_score: Mapped[float] = mapped_column(Float)
    corroboration_score: Mapped[float] = mapped_column(Float)
    operational_relevance: Mapped[float] = mapped_column(Float)

    time_sensitivity: Mapped[str] = mapped_column(String)
    deception_risk: Mapped[str] = mapped_column(String)

    involved_entities: Mapped[dict] = mapped_column(JSON)
    supporting_evidence: Mapped[dict] = mapped_column(JSON)

    report = relationship("HumintReport")
