# Project APEX Backend

FastAPI + SQLAlchemy backend scaffolding implementing the first wave of Project APEX data structures and CRUD APIs.

## What's implemented

- **Database layer**: SQLAlchemy `Base`, engine, and session management (`app/db/session.py`) plus one-shot table creation on startup (`app/db/init_db.py`).
- **Models**: Mission, Document, Entity, Event, and AgentRun ORM models with timestamp tracking, relationships, and JSON fields where required (`app/models/__init__.py`).
- **Schemas**: Pydantic create/response schemas for all models, with `orm_mode` for seamless serialization (`app/schemas/__init__.py`).
- **API routers**:
  - `POST/GET /missions` and `GET /missions/{mission_id}`
  - `POST/GET /missions/{mission_id}/documents`
  - `GET /missions/{mission_id}/graph` returning entities + events snapshot
  - `GET /missions/{mission_id}/agent_runs`
  - `POST /missions/{mission_id}/analyze` to trigger the agent pipeline
- **Agent pipeline services**: Configurable LLM client plus extraction, guardrail, and agent orchestration services (`app/services/*`) enabling end-to-end analysis with either demo data or real LLM calls.
- **FastAPI app**: Router registration and startup hook that auto-creates tables (`app/main.py`).

## Directory structure

```
apex/backend
└── app
    ├── __init__.py
    ├── api
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── documents.py
    │   ├── graph.py
    │   └── missions.py
    ├── db
    │   ├── __init__.py (implicit namespace)
    │   ├── init_db.py
    │   └── session.py
    ├── main.py
    ├── models
    │   └── __init__.py
    ├── services
    │   ├── __init__.py
    │   ├── agent_service.py
    │   ├── extraction_service.py
    │   ├── guardrail_service.py
    │   └── llm_client.py
    └── schemas
        └── __init__.py
```

## Running locally

1. Install dependencies (example):
   ```bash
   pip install fastapi uvicorn[standard] sqlalchemy pydantic
   ```
2. Start the API from the `backend` directory:
   ```bash
   uvicorn app.main:app --reload --app-dir backend
   ```
   The startup hook will auto-create the SQLite database (`app.db`).
3. Trigger a mission analysis run (after creating a mission & documents):
   ```bash
   curl -X POST http://localhost:8000/missions/1/analyze
   ```
   The response body contains the persisted `AgentRun` record.

### LLM configuration

The agent pipeline reads its LLM settings from environment variables (see `app/config_llm.py`). Defaults keep demo mode on, so no external calls are made until you override them.

| Variable              | Default value                              | Purpose                                  |
|-----------------------|--------------------------------------------|------------------------------------------|
| `APEX_LLM_BASE_URL`   | `http://localhost:11434/v1/chat`           | Chat completion endpoint URL             |
| `APEX_LLM_API_KEY`    | _empty_                                    | Bearer token for hosted providers        |
| `APEX_LLM_MODEL`      | `local-llm`                                | Model name sent to the endpoint          |
| `APEX_LLM_DEMO_MODE`  | `true`                                     | Keeps hard-coded responses when `true`   |

Set `APEX_LLM_DEMO_MODE=false` (and the other variables as needed) before running the API to enable real LLM calls.

## Next steps

- Introduce Alembic for managed migrations once schema becomes more complex.
- Add retries/metrics and provider-specific adapters around the LLM client.
- Flesh out Agent run mutation endpoints and real guardrail policies when specs are ready.
