from __future__ import annotations

import logging
from typing import Any, Dict

import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config_aggregator import get_aggregator_config
from app.services.llm_client import LLMClient
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["status"])

_llm_client = LLMClient()


async def _check_aggregator() -> str:
    cfg = get_aggregator_config()
    url = f"{cfg.base_url}/health"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return "ok"
            logger.warning("Aggregator health returned %s", resp.status_code)
            return "error"
    except Exception:
        logger.exception("Aggregator health check failed")
        return "error"


async def _check_llm() -> str:
    messages = [
        {"role": "system", "content": "You are a health check for APEX."},
        {"role": "user", "content": "Say OK."},
    ]
    try:
        _llm_client.chat(messages)
        return "ok"
    except Exception:
        logger.exception("LLM health check failed")
        return "error"


async def _warm_aggregator_profile() -> str:
    cfg = get_aggregator_config()
    url = f"{cfg.base_url}/profile"
    payload = {
        "sources": [
            {
                "type": "json_inline",
                "data": [
                    {
                        "warmup": True,
                        "message": "NexusCore warmup sample",
                    }
                ],
            }
        ],
        "options": {"sample_rows": 1},
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return "ok"
            logger.warning("Aggregator profile warmup returned %s", resp.status_code)
            return "error"
    except Exception:
        logger.exception("Aggregator profiling warmup failed")
        return "error"


def _warm_database() -> str:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.exception("Database warmup query failed")
        return "error"


async def _run_trivial_analysis() -> str:
    messages = [
        {
            "role": "system",
            "content": "You are NexusCore's analysis warmup task. Provide a short acknowledgement only.",
        },
        {
            "role": "user",
            "content": "Confirm the analysis stack has been preloaded by replying with READY.",
        },
    ]
    try:
        _llm_client.chat(messages)
        return "ok"
    except Exception:
        logger.exception("Trivial analysis warmup failed")
        return "error"


@router.get("/status")
async def status_check() -> JSONResponse:
    backend_status = "ok"
    aggregator_status = await _check_aggregator()
    llm_status = await _check_llm()

    overall = "ok"
    if aggregator_status != "ok" or llm_status != "ok":
        overall = "degraded"

    payload: Dict[str, Any] = {
        "overall": overall,
        "backend": backend_status,
        "aggregator": aggregator_status,
        "llm": llm_status,
    }

    http_status = (
        status.HTTP_200_OK if overall == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(content=payload, status_code=http_status)


@router.post("/warmup")
async def warmup() -> JSONResponse:
    aggregator_health, aggregator_profile = await _check_aggregator(), await _warm_aggregator_profile()
    llm_health = await _check_llm()
    trivial_analysis = await _run_trivial_analysis()
    db_status = _warm_database()

    components = {
        "aggregator_health": aggregator_health,
        "aggregator_profile": aggregator_profile,
        "llm": llm_health,
        "analysis": trivial_analysis,
        "database": db_status,
    }
    overall = "ok" if all(value == "ok" for value in components.values()) else "degraded"
    http_status = status.HTTP_200_OK if overall == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        content={"overall": overall, **components},
        status_code=http_status,
    )
