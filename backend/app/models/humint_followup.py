# backend/app/models/humint_followup.py

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, JSON, ForeignKey
from app.db.session import Base


class HumintFollowUpPlan(Base):
    __tablename__ = "humint_followup_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("humint_reports.id"), index=True)

    objective_summary: Mapped[str] = mapped_column(String)
    next_interview_questions: Mapped[dict] = mapped_column(JSON)
    verification_tasks: Mapped[dict] = mapped_column(JSON)
    engagement_notes: Mapped[dict] = mapped_column(JSON)

    report = relationship("HumintReport")
