from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent, documents, graph, missions, settings
from app.db.init_db import init_db


app = FastAPI(title="Project APEX Backend")

# Allow the Next.js frontend to talk to the API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

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


app.include_router(missions.router)
app.include_router(documents.router)
app.include_router(graph.router)
app.include_router(agent.router)
app.include_router(settings.router)
