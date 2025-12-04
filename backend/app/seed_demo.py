from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app import models
from app.db.session import Base, SessionLocal, engine

DEMO_MISSION_NAME = "Demo Mission – Sensor Traffic"
DEMO_MISSION_DESCRIPTION = (
    "Monitoring irregular packet bursts coming from forward sensor gateways. "
    "Demo mission includes documents, a profiled dataset, and semantic annotations."
)

DEMO_DOCUMENTS = [
    {
        "title": "Gateway overview",
        "content": (
            "Sensor gateways Alpha and Delta relay packet density metrics every minute. "
            "We are investigating why Gateway Delta shows latency spikes after midnight."
        ),
    },
    {
        "title": "Analyst notes",
        "content": (
            "Traffic burst on 2025-03-10 between 00:30–00:50Z with correlated power draw. "
            "Sensors 12A and 12B show the highest deviation from seasonal baseline."
        ),
    },
]

DEMO_SOURCES = [
    {
        "type": "inline_table",
        "name": "sensor_events",
        "records": [
            {
                "timestamp": "2025-03-10T00:45:00Z",
                "sensor_id": "12A",
                "gateway_id": "delta",
                "reading_value": 184.3,
                "status": "alert",
            }
        ],
    },
    {
        "type": "inline_table",
        "name": "gateway_health",
        "records": [
            {
                "captured_at": "2025-03-10T00:50:00Z",
                "gateway_id": "delta",
                "uptime_pct": 99.3,
                "active_sensors": 48,
            }
        ],
    },
]

DEMO_PROFILE = {
    "generated_at": "2025-03-10T01:15:00Z",
    "tables": [
        {
            "name": "sensor_events",
            "row_count": 1248,
            "sample": "Minute-level sensor packets",
            "columns": [
                {
                    "name": "timestamp",
                    "data_type": "TIMESTAMP",
                    "null_fraction": 0.0,
                    "min": "2025-03-09T12:00:00Z",
                    "max": "2025-03-10T01:10:00Z",
                },
                {
                    "name": "sensor_id",
                    "data_type": "STRING",
                    "null_fraction": 0.0,
                    "distinct_values": 52,
                },
                {
                    "name": "gateway_id",
                    "data_type": "STRING",
                    "null_fraction": 0.0,
                    "distinct_values": 4,
                },
                {
                    "name": "reading_value",
                    "data_type": "FLOAT",
                    "null_fraction": 0.01,
                    "min": 3.4,
                    "max": 612.8,
                },
                {
                    "name": "status",
                    "data_type": "STRING",
                    "null_fraction": 0.12,
                    "distinct_values": 3,
                },
            ],
        },
        {
            "name": "gateway_health",
            "row_count": 96,
            "sample": "Per-gateway telemetry",
            "columns": [
                {
                    "name": "captured_at",
                    "data_type": "TIMESTAMP",
                    "null_fraction": 0.0,
                },
                {
                    "name": "gateway_id",
                    "data_type": "STRING",
                    "null_fraction": 0.0,
                },
                {
                    "name": "uptime_pct",
                    "data_type": "FLOAT",
                    "null_fraction": 0.0,
                    "min": 97.4,
                    "max": 99.8,
                },
                {
                    "name": "active_sensors",
                    "data_type": "INTEGER",
                    "null_fraction": 0.0,
                    "min": 35,
                    "max": 52,
                },
            ],
        },
    ],
}

DEMO_SEMANTIC_PROFILE = {
    "columns": [
        {
            "name": "timestamp",
            "semantic_type": "datetime",
            "confidence": 0.97,
            "role": "event_time",
            "notes": "Ordering field for burst detection windows.",
        },
        {
            "name": "sensor_id",
            "semantic_type": "identifier",
            "confidence": 0.9,
            "role": "asset_id",
            "notes": "Maps back to individual fielded sensors.",
        },
        {
            "name": "gateway_id",
            "semantic_type": "infrastructure",
            "confidence": 0.86,
            "role": "ingest_node",
            "notes": "Gateway collecting packets from regional sensors.",
        },
        {
            "name": "reading_value",
            "semantic_type": "measurement",
            "confidence": 0.93,
            "role": "signal_value",
            "notes": "Normalized packet density score (0-600).",
        },
        {
            "name": "status",
            "semantic_type": "categorical",
            "confidence": 0.74,
            "role": "alert_state",
            "notes": "Flag indicating whether the reading breached alert thresholds.",
        },
    ],
    "version": "demo-1",
}


def _upsert_mission(session: Session) -> models.Mission:
    mission = session.query(models.Mission).filter(models.Mission.name == DEMO_MISSION_NAME).first()
    if mission is None:
        mission = models.Mission(name=DEMO_MISSION_NAME, description=DEMO_MISSION_DESCRIPTION)
        session.add(mission)
    else:
        mission.description = DEMO_MISSION_DESCRIPTION
    session.commit()
    session.refresh(mission)
    return mission


def _ensure_documents(session: Session, mission: models.Mission) -> None:
    for doc in DEMO_DOCUMENTS:
        existing = (
            session.query(models.Document)
            .filter(models.Document.mission_id == mission.id, models.Document.title == doc["title"])
            .first()
        )
        if existing:
            existing.content = doc["content"]
            existing.include_in_analysis = True
        else:
            session.add(
                models.Document(
                    mission_id=mission.id,
                    title=doc["title"],
                    content=doc["content"],
                    include_in_analysis=True,
                )
            )
    session.commit()


def _ensure_dataset(session: Session, mission: models.Mission) -> None:
    dataset = (
        session.query(models.MissionDataset)
        .filter(models.MissionDataset.mission_id == mission.id, models.MissionDataset.name == "Sensor packet profile")
        .first()
    )
    if dataset is None:
        dataset = models.MissionDataset(mission_id=mission.id, name="Sensor packet profile")
    dataset.status = "ready"
    dataset.sources = DEMO_SOURCES
    dataset.profile = DEMO_PROFILE
    dataset.semantic_profile = DEMO_SEMANTIC_PROFILE
    session.add(dataset)
    session.commit()


def seed_demo() -> None:
    """Seed demo mission, documents, and dataset for immediate semantic profiling demos."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        mission = _upsert_mission(session)
        _ensure_documents(session, mission)
        _ensure_dataset(session, mission)
        print("✅ Demo data ready for mission:", mission.name)
    finally:
        session.close()


def main() -> None:
    seed_demo()


if __name__ == "__main__":
    main()
