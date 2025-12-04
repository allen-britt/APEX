from uuid import uuid4

from sqlalchemy import Boolean, JSON, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.authorities import AuthorityType, normalize_authority
# Ensure HUMINT models are imported so SQLAlchemy can resolve relationships
from app.models.humint_report import HumintReport  # noqa: E402,F401
from app.models.humint_insight import HumintInsight  # noqa: E402,F401
from app.models.humint_followup import HumintFollowUpPlan  # noqa: E402,F401


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    primary_authority = Column(
        "mission_authority",
        String,
        nullable=False,
        default=AuthorityType.LEO.value,
        server_default=AuthorityType.LEO.value,
    )
    original_authority = Column(
        String,
        nullable=False,
        default=AuthorityType.LEO.value,
        server_default=AuthorityType.LEO.value,
    )
    secondary_authorities = Column(JSON, nullable=False, default=list, server_default="[]")
    int_types = Column(JSON, nullable=False, default=list, server_default="[]")
    kg_namespace = Column(String, nullable=True, unique=True)
    gap_analysis = Column(JSON, nullable=True)
    template_reports = Column(JSON, nullable=False, default=list, server_default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    documents = relationship("Document", back_populates="mission", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="mission", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="mission", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="mission", cascade="all, delete-orphan")
    datasets = relationship(
        "MissionDataset",
        back_populates="mission",
        cascade="all, delete-orphan",
    )
    mission_documents = relationship(
        "MissionDocument",
        back_populates="mission",
        cascade="all, delete-orphan",
    )
    authority_pivots = relationship(
        "MissionAuthorityPivot",
        back_populates="mission",
        cascade="all, delete-orphan",
        order_by="MissionAuthorityPivot.created_at.asc()",
    )
    humint_reports = relationship(
        "HumintReport",
        back_populates="mission",
        cascade="all, delete-orphan",
    )

    @property
    def mission_authority(self) -> str:
        return self.primary_authority

    @mission_authority.setter
    def mission_authority(self, value: str) -> None:
        self.primary_authority = normalize_authority(value).value


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    include_in_analysis = Column(Boolean, nullable=False, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mission = relationship("Mission", back_populates="documents")


class MissionDocument(Base):
    __tablename__ = "mission_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    mission_id = Column(Integer, ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String, nullable=False)
    title = Column(String, nullable=True)
    original_path = Column(String, nullable=True)
    primary_int = Column(String, nullable=True)
    int_types = Column(JSON, nullable=False, default=list, server_default="[]")
    aggregator_doc_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="PENDING", server_default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mission = relationship("Mission", back_populates="mission_documents")
    ingest_job = relationship(
        "MissionIngestJob",
        back_populates="document",
        uselist=False,
        passive_deletes=True,
    )

    @property
    def ingest_status(self) -> str | None:  # pragma: no cover - simple accessor
        if self.ingest_job:
            return self.ingest_job.status
        return None

    @property
    def ingest_error(self) -> str | None:  # pragma: no cover - simple accessor
        if self.ingest_job:
            return self.ingest_job.last_error
        return None

    @property
    def kg_nodes_before(self) -> int | None:  # pragma: no cover - simple accessor
        if self.ingest_job:
            return self.ingest_job.nodes_before
        return None

    @property
    def kg_nodes_after(self) -> int | None:  # pragma: no cover - simple accessor
        if self.ingest_job:
            return self.ingest_job.nodes_after
        return None

    @property
    def kg_edges_before(self) -> int | None:  # pragma: no cover - simple accessor
        if self.ingest_job:
            return self.ingest_job.edges_before
        return None

    @property
    def kg_edges_after(self) -> int | None:  # pragma: no cover - simple accessor
        if self.ingest_job:
            return self.ingest_job.edges_after
        return None

    @property
    def kg_nodes_delta(self) -> int | None:  # pragma: no cover - simple accessor
        if self.kg_nodes_before is None or self.kg_nodes_after is None:
            return None
        return self.kg_nodes_after - self.kg_nodes_before

    @property
    def kg_edges_delta(self) -> int | None:  # pragma: no cover - simple accessor
        if self.kg_edges_before is None or self.kg_edges_after is None:
            return None
        return self.kg_edges_after - self.kg_edges_before


class MissionIngestJob(Base):
    __tablename__ = "mission_ingest_jobs"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("mission_documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String, nullable=False, default="PENDING", server_default="PENDING")
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    last_error = Column(Text, nullable=True)
    payload_text = Column(Text, nullable=False, default="", server_default="")
    metadata_blob = Column(JSON, nullable=False, default=dict, server_default="{}")
    nodes_before = Column(Integer, nullable=True)
    edges_before = Column(Integer, nullable=True)
    nodes_after = Column(Integer, nullable=True)
    edges_after = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    mission = relationship("Mission")
    document = relationship("MissionDocument", back_populates="ingest_job")


class MissionAuthorityPivot(Base):
    __tablename__ = "mission_authority_pivots"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    from_authority = Column(String, nullable=False)
    to_authority = Column(String, nullable=False)
    justification = Column(Text, nullable=False)
    risk = Column(String, nullable=False)
    allowed = Column(Boolean, nullable=False, default=True, server_default="1")
    conditions = Column(JSON, nullable=False, default=list, server_default="[]")
    actor = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mission = relationship("Mission", back_populates="authority_pivots")


class MissionDataset(Base):
    __tablename__ = "mission_datasets"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ready")
    sources = Column(JSON, nullable=False, default=list)
    profile = Column(JSON, nullable=True)
    semantic_profile = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    mission = relationship("Mission", back_populates="datasets")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mission = relationship("Mission", back_populates="entities")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    location = Column(String, nullable=True)
    involved_entity_ids = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mission = relationship("Mission", back_populates="events")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="queued")
    summary = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    guardrail_status = Column(String, nullable=False, default="ok")
    guardrail_issues = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    mission = relationship("Mission", back_populates="agent_runs")
