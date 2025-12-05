import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agent,
    analysis,
    documents,
    graph,
    health,
    humint,
    mission_datasets,
    missions,
    report,
    settings,
    status as status_api,
)
from app.api import models as models_api
from app.db.init_db import init_db


app = FastAPI(title="Project APEX Backend")


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("BACKEND_CORS_ORIGINS")
    if not raw:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    entries = [origin.strip() for origin in raw.split(",")]
    return [origin for origin in entries if origin]


origins = _parse_cors_origins() or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(health.router)
app.include_router(status_api.router)
app.include_router(missions.router)
app.include_router(documents.router)
app.include_router(mission_datasets.router)
app.include_router(graph.router)
app.include_router(analysis.router)
app.include_router(humint.router)
app.include_router(agent.router)
app.include_router(report.router)
app.include_router(settings.router)
app.include_router(models_api.router)
