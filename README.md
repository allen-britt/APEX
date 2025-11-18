# Project APEX

Project APEX is an experiment in **agentic, multi-source intelligence analysis**.

It ingests a set of mission documents (HUMINT, SIGINT, OSINT, etc.), runs them through a profile-aware LLM pipeline, and produces a structured picture of a mission space:

- Entities (people, places, facilities, items)
- Events and timeline
- Cross-document insights
- Gaps and guardrail notes
- A full mission report you can export or brief from

> Think: a junior intel analyst that never gets tired of reading PDFs.

---

## High-level architecture

The repo is split into a **FastAPI backend** and a **Next.js frontend**:

```text
APEX/
├── backend/          # FastAPI app
│   └── app/
│       ├── api/      # Mission, documents, agent, graph, settings
│       ├── db/       # SQLAlchemy engine + session
│       ├── models/   # Mission, Document, Entity, Event, AgentRun
│       ├── schemas/  # Pydantic schemas
│       ├── services/ # LLM client, extraction, guardrails, agent pipeline
│       ├── config_llm.py
│       └── main.py   # FastAPI app entrypoint
└── frontend/         # Next.js 14 app
    ├── app/          # Routes (/, /missions/[id], /missions/[id]/report, /settings)
    ├── components/   # Mission cards, document list, model selector, report view, etc.
    └── lib/          # API helpers for talking to the backend
```

### Backend

FastAPI for HTTP API.  
SQLAlchemy for persistence:

- Mission
- Document
- Entity
- Event
- AgentRun

Services:

- `llm_client` — profile-aware chat client with:
  - Local or hosted models
  - Demo mode (stub responses)
  - Fallback logic when the LLM is offline
- `extraction_service` — builds mission context and extracts entities/events.
- `guardrail_service` — heuristic + LLM-based analytic guardrails.
- `agent_service` — orchestrates the multi-stage analysis chain:
  - Raw facts
  - Entities & events
  - Cross-document reasoning
  - Gaps
  - Operational estimate
  - Next steps
  - Delta vs previous run

### Frontend

Next.js 14 / React / TypeScript

Pages:

- `/` — mission list and quick status.
- `/missions/[id]` — mission detail, documents, run history, graph.
- `/missions/[id]/report` — printable mission report.
- `/settings` — model selection and basic config.

Components:

- Mission cards + actions (delete, view).
- Document manager (add, move between missions, toggle include-in-analysis, delete).
- Model selector (active LLM).
- Report view (structured output of the latest run).

## Getting started

### Prereqs

- Python 3.10+
- Node.js 18+
- npm or yarn
- (Optional) Local LLM server (e.g. Ollama) listening on an OpenAI-compatible chat endpoint

### 1. Backend setup

From the backend directory:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # or pip install fastapi uvicorn[standard] sqlalchemy httpx pydantic
```

Configure LLM behavior via environment variables:

```bash
# .env (example)
APEX_LLM_BASE_URL=http://localhost:11434/v1/chat/completions
APEX_LLM_API_KEY=
APEX_LLM_MODEL=local-llm
APEX_LLM_DEMO_MODE=true  # set to false when your LLM endpoint is ready
APEX_MODEL_CONFIG_PATH=./model_config.json
```

Run the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On first run, APEX will create a SQLite database (e.g. `app.db`) and the required tables.  
Open the API docs at: <http://localhost:8000/docs>

### 2. Frontend setup

From the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Visit: <http://localhost:3000>  
Make sure the backend is running on `http://localhost:8000` (the frontend expects this by default).

## Typical workflow

### Create a mission

- From the home page, create a new mission (title + description).
- It appears in the mission list.

### Attach documents

- Open the mission.
- Add multiple documents (HUMINT, SIGINT, OSINT, etc.).
- Optionally:
  - Collapse/expand document previews.
  - Toggle *Include in analysis* per document.
  - Move a document to a different mission.
  - Delete a document.

### Run analysis

- Click **Run Analysis**.
- The backend runs the agent pipeline:
  - Builds context from included documents.
  - Calls the LLM for raw facts, entities, events.
  - Computes cross-document insights, gaps, estimates, next steps.
  - Stores an AgentRun with all artifacts.

### Explore results

On the mission detail page:

- See the latest summary, operational estimate, guardrail status.
- Inspect entities and events via the graph endpoint.
- See run history.

### Generate a mission report

- Click **View Report** (or navigate to `/missions/[id]/report`).
- You get a structured, printable report with:
  - Mission overview and objectives
  - Source documents table
  - Latest analysis summary + estimate
  - Cross-document insights
  - Recommended next steps
  - Guardrails & confidence
  - Entities and timeline
- Use the browser print dialog to export to PDF.

## Model configuration

APEX can be pointed at different models via the backend config and the frontend settings page.

Key env vars (see `app/config_llm.py`):

- `APEX_LLM_BASE_URL` – chat completion endpoint URL.
- `APEX_LLM_API_KEY` – bearer token for hosted providers.
- `APEX_LLM_MODEL` – model name string the endpoint expects.
- `APEX_LLM_DEMO_MODE` – when true, the pipeline uses stubbed outputs.
- `APEX_MODEL_CONFIG_PATH` – optional JSON file where the active model is persisted.

The `/settings` page calls:

- `GET /models/available` – list of models APEX discovers (e.g., via Ollama or static config).
- `GET /settings/model` / `POST /settings/model` – read/write active model.

## Roadmap

Planned enhancements:

- Multi-profile analysis (HUMINT / SIGINT / OSINT toggles in the UI).
- Richer graph visualizations in the frontend.
- More report templates (command 1-pager, delta update).
- Export pipeline (PDF, DOCX) with classification wrappers.
- Optional RAG integration over doctrine or unit-specific references.

Contributions, ideas, and weird mission scenarios welcome.