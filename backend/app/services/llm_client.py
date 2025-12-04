"""Configurable LLM client for Project APEX.

Supports both demo (stub) mode and real HTTP calls to an OpenAI-compatible
chat-completion endpoint.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, TypedDict, TypeVar

import httpx

from app.config_llm import (
    get_active_llm_name,
    get_available_llms,
    get_llm_by_name,
    get_llm_config,
    is_demo_mode,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

Role = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: Role
    content: str


class LlmError(Exception):
    """Raised when an LLM request fails."""


class LLMClient:
    """Unified client for local LLMs (Ollama or other backends)."""

    def __init__(self, timeout: float = 60.0) -> None:
        self._timeout = timeout

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"name": model.name, "display_name": model.display_name, "kind": model.kind}
            for model in get_available_llms()
        ]

    def _call_ollama_chat(
        self,
        *,
        base_url: str,
        model_name: str,
        messages: List[ChatMessage],
        timeout: float | None = None,
    ) -> str:
        url = f"{base_url.rstrip('/')}/api/chat"
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
        }

        request_timeout = timeout or self._timeout
        try:
            logger.debug("Calling Ollama chat at %s with model=%s", url, model_name)
            response = httpx.post(url, json=payload, timeout=request_timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network paths
            logger.exception("LLM request failed (Ollama)")
            raise LlmError("LLM request to Ollama failed") from exc

        data = response.json()
        try:
            return data["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected Ollama response: %s", data)
            raise LlmError("Unexpected Ollama response format") from exc

    def chat(self, messages: List[ChatMessage], *, timeout: float | None = None) -> str:
        active_name = get_active_llm_name()
        cfg = get_llm_by_name(active_name)

        if cfg.kind == "ollama_chat":
            return self._call_ollama_chat(
                base_url=cfg.base_url,
                model_name=cfg.name,
                messages=messages,
                timeout=timeout,
            )

        raise LlmError(f"Unsupported LLM engine kind: {cfg.kind!r}")


_CHAT_CLIENT = LLMClient()

_active_model: str | None = None


def _model_store_path() -> Path:
    config = get_llm_config()
    return Path(config.model_config_path)


def _load_model_override() -> str | None:
    path = _model_store_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        value = str(data.get("model", "")).strip()
        return value or None
    except Exception:  # pragma: no cover - best-effort logging
        logger.warning("Failed to load model override from %s", path, exc_info=True)
        return None


def get_active_model() -> str:
    global _active_model
    if _active_model:
        return _active_model

    override = _load_model_override()
    if override:
        _active_model = override
    else:
        _active_model = get_llm_config().model
    return _active_model


def set_active_model(model: str) -> None:
    global _active_model
    candidate = (model or "").strip()
    if not candidate:
        raise ValueError("Model name must be non-empty")

    _active_model = candidate
    path = _model_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": candidate}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


RAW_FACTS_SYSTEM_PROMPT = (
    "You are an intelligence analyst extracting atomic facts from mission material."
    " Output ONLY JSON as instructed."
)

GAP_SYSTEM_PROMPT = (
    "You are an all-source analyst identifying collection gaps and follow-up questions."
    " Output ONLY the requested JSON."
)

ESTIMATE_SYSTEM_PROMPT = (
    "You are producing an operational estimate for Project APEX. Provide an analytical,"
    " prose narrative grounded only in the supplied context."
)

DELTA_SYSTEM_PROMPT = (
    "You compare successive intelligence updates and describe what changed, remained"
    " constant, or escalated. Respond in concise prose."
)

CROSS_DOC_SYSTEM_PROMPT = (
    "You are an all-source intelligence analyst performing cross-document reasoning."
    " Respond ONLY with the requested JSON object."
)

SELF_VERIFY_SYSTEM_PROMPT = (
    "You are reviewing your own intelligence assessment for internal consistency and errors."
    " Respond ONLY with the requested JSON object."
)

GUARDRAIL_REVIEW_SYSTEM_PROMPT = (
    "You validate intelligence assessments for analytic quality, sourcing, and red flags."
    " Respond ONLY with the requested JSON object."
)


class LLMCallException(Exception):
    """Raised when the LLM call fails or returns malformed data."""


DEMO_ENTITIES = [
    {
        "name": "Sentinel Drone",
        "type": "asset",
        "description": "Autonomous aerial reconnaissance platform.",
    },
    {
        "name": "Operative Vega",
        "type": "person",
        "description": "Field agent overseeing drone deployment.",
    },
]

DEMO_FACTS = [
    {
        "statement": "Sentinel Drone conducted reconnaissance over Sector 7",
        "confidence": 0.88,
        "source_refs": ["Recon Flight Log"],
    },
    {
        "statement": "Operative Vega briefed command on anomalies detected",
        "confidence": 0.82,
        "source_refs": ["Briefing Notes"],
    },
    {
        "statement": "Thermal readings spiked near Bravo checkpoint",
        "confidence": 0.75,
        "source_refs": ["Thermal Scan"],
    },
]

DEMO_GAPS = {
    "gaps": [
        {
            "description": "Need confirmation on hostile presence causing thermal spike",
            "priority": "high",
            "recommended_questions": [
                "Can reconnaissance assets obtain visual confirmation of the anomaly?",
                "Are there HUMINT sources near Bravo checkpoint?",
            ],
        },
        {
            "description": "Communications route for relaying drone telemetry remains unclear",
            "priority": "medium",
            "recommended_questions": [
                "Which network path is carrying the drone feed?",
                "Is there encryption in place on the uplink?",
            ],
        },
    ]
}

DEMO_OPERATIONAL_ESTIMATE = (
    "Sentinel Drone patrols continue to surveil Sector 7, where irregular thermal signatures"
    " persist near Bravo checkpoint. Operative Vega and the forward detachment remain postured"
    " to investigate the anomaly once corroborating intelligence is received."
    "\n\nThe adversary has not revealed overt force dispositions but likely maintains a small"
    " technical element in the area to mask activity. Friendly reconnaissance capacity"
    " remains adequate, yet the mission hinges on rapidly validating the anomaly before"
    " conditions degrade. Risk is moderate given uncertain hostile intent and limited"
    " communications resiliency."
)

DEMO_DELTA_SUMMARY = (
    "New reconnaissance sorties identified persistent anomalies in Sector 7, but no direct"
    " hostile contact has occurred since the prior run. Friendly posture is unchanged,"
    " though emphasis shifted toward validating the unexplained thermal spike. Overall"
    " risk remains steady pending additional collection."
)

DEMO_CROSS_DOCUMENT = {
    "corroborated_findings": [
        "Thermal anomalies near Bravo checkpoint align with drone telemetry and field notes",
    ],
    "contradictions": [
        "Briefing claims enemy withdrawal while SIGINT suggests continued transmissions",
    ],
    "notable_trends": [
        "Increased emphasis on validating anomalies before committing forces",
    ],
}

DEMO_SELF_VERIFY = {
    "internal_consistency": "good",
    "confidence_adjustment": 0.0,
    "notes": [
        "Assessment aligns with observed facts; no major contradictions detected.",
    ],
}

DEMO_GUARDRAIL_REVIEW = {
    "status": "OK",
    "issues": [],
}

DEMO_EVENTS = [
    {
        "title": "Initial recon flight",
        "summary": "Sentinel Drone captured thermal readings over Sector 7.",
        "timestamp": "2025-11-10T09:30:00+00:00",
        "location": "Sector 7",
        "involved_entity_ids": [],
    },
    {
        "title": "Operator briefing",
        "summary": "Operative Vega briefed command on reconnaissance anomalies.",
        "timestamp": "2025-11-11T15:00:00+00:00",
        "location": "Forward Ops Center",
        "involved_entity_ids": [],
    },
]

PROFILE_FOCUS = {
    "humint": "Emphasize PERSON, GROUP, ORGANIZATION, LOCATION, FACILITY, and intent relationships.",
    "sigint": "Emphasize PLATFORM, NODE, NETWORK, FREQUENCY, SIGNAL, SENSOR, and technical infrastructure.",
    "osint": "Emphasize ORGANIZATION, MEDIA_OUTLET, WEBSITE, COMPANY, EVENT, and public indicators.",
}


EXTRACTION_SYSTEM_PROMPT = (
    "You are an intelligence extraction engine supporting Project APEX."
    " You must return ONLY valid JSON arrays with no commentary, preamble, or explanation."
)

SUMMARY_TASK_INSTRUCTIONS = (
    "You are summarizing the mission for decision makers."
    " Provide a concise narrative (<=120 words) focused on intent, capabilities, and risk."
    " Use the structured entities/events and KG context only."  # enforcement handled upstream
)

NEXT_STEPS_TASK_INSTRUCTIONS = (
    "You recommend tactical next steps"
    " grounded only in the structured context provided."
)

META_BAN_RULES = (
    "Do NOT mention 'mission text', 'JSON', 'context', 'Agent Run Advisory', internal variable names (e.g., evidence.incidents[0]), or Event IDs in your response."
)

SUMMARY_SYSTEM_PROMPT = (
    "You are a strategic intelligence analyst. Produce concise, objective assessments "
    "based solely on the provided structured context. "
    f"{META_BAN_RULES}"
)

NEXT_STEPS_SYSTEM_PROMPT = (
    "You are an operations planner. Recommend actionable follow-up steps based on the structured context. "
    f"{META_BAN_RULES}"
)


def _profile_hint(profile: str) -> str:
    return PROFILE_FOCUS.get(profile.lower(), PROFILE_FOCUS["humint"])


async def _call_llm(
    prompt: str,
    system: str | None = None,
    *,
    policy_block: str | None = None,
) -> str:
    """Invoke the active local LLM via the unified LLMClient."""

    messages: List[ChatMessage] = []
    combined_system = "\n\n".join(part for part in (policy_block, system) if part)
    if combined_system:
        messages.append({"role": "system", "content": combined_system})
    messages.append({"role": "user", "content": prompt})

    try:
        return _CHAT_CLIENT.chat(messages)
    except LlmError as exc:  # pragma: no cover - simple logging path
        logger.exception("LLM chat call failed")
        raise LLMCallException("LLM chat call failed") from exc


def _build_entity_prompt(text: str, profile: str) -> str:
    focus = _profile_hint(profile)
    return (
        f"Analysis profile: {profile.upper()} - {focus}\n"
        "Extract mission-relevant entities aligned with this focus.\n"
        "Output MUST be a JSON array. Each entity object requires keys: name (string), type (string), description (string).\n"
        "Be specific with `type` (e.g., PERSON, FACILITY, NETWORK, PLATFORM).\n"
        "Mission text to analyze:\n"
        f"{text}\n"
        "Return ONLY JSON."
    )


def _build_event_prompt(text: str, profile: str) -> str:
    focus = _profile_hint(profile)
    return (
        f"Analysis profile: {profile.upper()} - {focus}\n"
        "Identify discrete mission events (who/what/when/where).\n"
        "Return a JSON array of objects with keys: title, summary, timestamp (ISO8601 or null), location (string or null), involved_entity_ids (array, leave empty).\n"
        "Infer timestamps and locations when clearly implied (e.g., 'at 0930Z', 'near Bravo checkpoint').\n"
        "Mission text to analyze:\n"
        f"{text}\n"
        "Return ONLY JSON."
    )


def _serialize_context(entities: List[dict], events: List[dict]) -> str:
    return json.dumps({"entities": entities, "events": events}, ensure_ascii=False, indent=2)


def _serialize_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _deepcopy_stub(value: T) -> T:
    return json.loads(json.dumps(value))


async def _with_llm_fallback(
    *,
    prompt: str,
    system: str | None,
    parse: Callable[[str], T],
    stub: Callable[[], T],
    policy_block: str | None = None,
) -> T:
    if is_demo_mode():
        logger.info("LLM demo mode active, returning stubbed data.")
        return stub()

    try:
        raw = await _call_llm(prompt, system=system, policy_block=policy_block)
        return parse(raw)
    except Exception:
        logger.warning("LLM call failed or response invalid; falling back to stub", exc_info=True)
        return stub()


async def extract_entities(
    text: str,
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> List[dict]:
    prompt = _build_entity_prompt(text, profile)

    def _parse(raw: str) -> List[dict]:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("Entity payload must be a list")
        return data

    return await _with_llm_fallback(
        prompt=prompt,
        system=EXTRACTION_SYSTEM_PROMPT,
        parse=_parse,
        stub=lambda: _deepcopy_stub(DEMO_ENTITIES),
        policy_block=policy_block,
    )


async def extract_events(
    text: str,
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> List[dict]:
    prompt = _build_event_prompt(text, profile)

    def _parse(raw: str) -> List[dict]:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("Event payload must be a list")
        return data

    return await _with_llm_fallback(
        prompt=prompt,
        system=EXTRACTION_SYSTEM_PROMPT,
        parse=_parse,
        stub=lambda: _deepcopy_stub(DEMO_EVENTS),
        policy_block=policy_block,
    )


async def summarize_mission(
    entities: List[dict],
    events: List[dict],
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> str:
    guardrail = (
        "You are an intelligence analyst supporting this mission."
        " Use ONLY the entities/events JSON."
        " Do NOT invent new incidents, locations, or organizations."
        " Do NOT mention JSON, mission text, context, Agent Run Advisory, or variable names like Event ID 3 or evidence.incidents[0]."
        " If data is missing, note 'None available'."
        " Write as a final product, not as an explanation of inputs."
    )
    context_json = _serialize_context(entities, events)
    prompt = (
        f"Analysis profile: {profile.upper()} - {_profile_hint(profile)}\n"
        f"{guardrail}\n"
        "Task: Produce a concise (<=120 words) analytic summary highlighting intent, capabilities, and assessed risk without referencing JSON or 'context'.\n"
        "Input JSON (entities + events):\n"
        f"{context_json}"
    )

    def _stub() -> str:
        entity_names = ", ".join(entity.get("name", "Unknown") for entity in entities) or "Unknown entities"
        event_titles = ", ".join(event.get("title", "Event") for event in events) or "no recorded events"
        return f"Mission involves entities: {entity_names}. Recent events include: {event_titles}."

    return await _with_llm_fallback(
        prompt=prompt,
        system=SUMMARY_SYSTEM_PROMPT,
        parse=lambda raw: raw,
        stub=_stub,
        policy_block=policy_block,
    )


async def suggest_next_steps(
    entities: List[dict],
    events: List[dict],
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> str:
    guardrail = (
        "You are an intelligence analyst recommending lawful next steps for this mission."
        " Use ONLY the entities/events JSON."
        " Do NOT invent new proper nouns or authorities."
        " Do NOT mention JSON, mission text, context, Agent Run Advisory, or variable names like Event ID 3 or evidence.incidents[0]."
        " If information is missing, state that a prerequisite is needed."
        " Write as final tasking guidance, not as meta commentary."
    )
    context_json = _serialize_context(entities, events)
    prompt = (
        f"Analysis profile: {profile.upper()} - {_profile_hint(profile)}\n"
        f"{guardrail}\n"
        "Task: Recommend 3-7 actionable next steps (collection, coordination, verification, or tasking) tied to the available evidence."
        " Respond with a brief numbered list or bullet list without referencing JSON.\n"
        "Input JSON (entities + events):\n"
        f"{context_json}"
    )

    def _stub() -> str:
        if not events:
            return "Review mission scope and gather additional field intelligence."
        location = events[-1].get("location", "the field")
        return (
            "Deploy Operative Vega to validate drone telemetry anomalies in "
            f"{location} and schedule a follow-up briefing."
        )

    return await _with_llm_fallback(
        prompt=prompt,
        system=NEXT_STEPS_SYSTEM_PROMPT,
        parse=lambda raw: raw,
        stub=_stub,
        policy_block=policy_block,
    )


async def extract_raw_facts(
    text: str,
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> List[dict]:
    prompt = (
        f"Analysis profile: {profile.upper()} - {_profile_hint(profile)}\n"
        "Extract atomic mission facts. Each fact must be a single statement without conjunctions.\n"
        "Output MUST be a JSON array of objects with keys: statement (string), confidence (0-1 float), source_refs (array of strings).\n"
        "Mission text:\n"
        f"{text}\n"
        "Return ONLY JSON."
    )

    def _parse(raw: str) -> List[dict]:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("Raw facts payload must be a list")
        return data

    return await _with_llm_fallback(
        prompt=prompt,
        system=RAW_FACTS_SYSTEM_PROMPT,
        parse=_parse,
        stub=lambda: _deepcopy_stub(DEMO_FACTS),
        policy_block=policy_block,
    )


async def detect_information_gaps(
    facts: List[dict],
    entities: List[dict],
    events: List[dict],
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> dict:
    payload = {
        "profile": profile,
        "facts": facts,
        "entities": entities,
        "events": events,
    }
    prompt = (
        "Identify missing information that would materially improve this analysis.\n"
        "Return ONLY JSON with the schema: {\"gaps\": [{\"description\": str, \"priority\": \"high|medium|low\", \"recommended_questions\": [str]}]}\n"
        "Context JSON follows:\n"
        f"{_serialize_payload(payload)}"
    )

    def _parse(raw: str) -> dict:
        data = json.loads(raw)
        gaps = data.get("gaps") if isinstance(data, dict) else None
        if not isinstance(gaps, list):
            raise ValueError("Information gaps payload missing 'gaps'")
        return data

    return await _with_llm_fallback(
        prompt=prompt,
        system=GAP_SYSTEM_PROMPT,
        parse=_parse,
        stub=lambda: _deepcopy_stub(DEMO_GAPS),
        policy_block=policy_block,
    )


async def generate_operational_estimate(
    facts: List[dict],
    entities: List[dict],
    events: List[dict],
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> str:
    payload = {
        "profile": profile,
        "facts": facts,
        "entities": entities,
        "events": events,
    }
    prompt = (
        f"Analysis profile: {profile.upper()} - {_profile_hint(profile)}\n"
        "Produce a 2-3 paragraph operational estimate covering situation, enemy/target, friendly considerations, and risk assessment.\n"
        "Use ONLY the structured context below:\n"
        f"{_serialize_payload(payload)}"
    )

    return await _with_llm_fallback(
        prompt=prompt,
        system=ESTIMATE_SYSTEM_PROMPT,
        parse=lambda raw: raw,
        stub=lambda: DEMO_OPERATIONAL_ESTIMATE,
        policy_block=policy_block,
    )


async def generate_run_delta(
    previous_summary: str | None,
    previous_events: List[dict],
    current_summary: str,
    current_events: List[dict],
    *,
    policy_block: str | None = None,
) -> str:
    payload = {
        "previous_summary": previous_summary,
        "previous_events": previous_events,
        "current_summary": current_summary,
        "current_events": current_events,
    }
    prompt = (
        "Compare the prior and current updates. Describe what is new, what remains unchanged, and any escalation/de-escalation.\n"
        "Respond with 1-2 short paragraphs.\n"
        f"Context JSON:\n{_serialize_payload(payload)}"
    )

    return await _with_llm_fallback(
        prompt=prompt,
        system=DELTA_SYSTEM_PROMPT,
        parse=lambda raw: raw,
        stub=lambda: DEMO_DELTA_SUMMARY,
        policy_block=policy_block,
    )


async def cross_document_analysis(
    facts: List[dict],
    entities: List[dict],
    events: List[dict],
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> dict:
    payload = {
        "profile": profile,
        "facts": facts,
        "entities": entities,
        "events": events,
    }
    prompt = (
        f"Analysis profile: {profile.upper()} - {_profile_hint(profile)}\n"
        "Identify corroborated findings, contradictions, and notable trends observed across documents.\n"
        "Return ONLY JSON with keys: corroborated_findings (list of strings), contradictions (list of strings), notable_trends (list of strings).\n"
        f"Context JSON:\n{_serialize_payload(payload)}"
    )

    def _parse(raw: str) -> dict:
        data = json.loads(raw)
        for key in ("corroborated_findings", "contradictions", "notable_trends"):
            values = data.get(key)
            if not isinstance(values, list):
                raise ValueError(f"Cross-document payload missing list for {key}")
        return data

    return await _with_llm_fallback(
        prompt=prompt,
        system=CROSS_DOC_SYSTEM_PROMPT,
        parse=_parse,
        stub=lambda: _deepcopy_stub(DEMO_CROSS_DOCUMENT),
        policy_block=policy_block,
    )


async def self_verify_assessment(
    facts: List[dict],
    entities: List[dict],
    events: List[dict],
    summary: str,
    estimate: str,
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> dict:
    payload = {
        "profile": profile,
        "facts": facts,
        "entities": entities,
        "events": events,
        "summary": summary,
        "estimate": estimate,
    }
    prompt = (
        f"Analysis profile: {profile.upper()} - {_profile_hint(profile)}\n"
        "Evaluate the internal consistency of this assessment. Identify obvious contradictions or missing logic.\n"
        "Return ONLY JSON with keys: internal_consistency (good|questionable|poor), confidence_adjustment (float in [-0.5,0.5]), notes (list of strings).\n"
        f"Context JSON:\n{_serialize_payload(payload)}"
    )

    def _parse(raw: str) -> dict:
        data = json.loads(raw)
        consistency = data.get("internal_consistency")
        if consistency not in {"good", "questionable", "poor"}:
            raise ValueError("Self-verification payload missing internal_consistency")
        adj = data.get("confidence_adjustment")
        if not isinstance(adj, (int, float)):
            raise ValueError("Self-verification payload missing numeric confidence_adjustment")
        notes = data.get("notes", [])
        if not isinstance(notes, list):
            raise ValueError("Self-verification payload missing notes list")
        return data

    return await _with_llm_fallback(
        prompt=prompt,
        system=SELF_VERIFY_SYSTEM_PROMPT,
        parse=_parse,
        stub=lambda: _deepcopy_stub(DEMO_SELF_VERIFY),
        policy_block=policy_block,
    )


async def guardrail_quality_review(
    summary: str,
    estimate: str,
    gaps: dict,
    cross: dict,
    profile: str = "humint",
    *,
    policy_block: str | None = None,
) -> dict:
    payload = {
        "profile": profile,
        "summary": summary,
        "estimate": estimate,
        "gaps": gaps,
        "cross": cross,
    }
    prompt = (
        f"Analysis profile: {profile.upper()} - {_profile_hint(profile)}\n"
        "Evaluate this assessment for analytic quality, sourcing, and red flags.\n"
        "Return ONLY JSON with keys: status (OK|CAUTION|REVIEW) and issues (list of strings).\n"
        f"Context JSON:\n{_serialize_payload(payload)}"
    )

    def _parse(raw: str) -> dict:
        data = json.loads(raw)
        status = (data.get("status") or "OK").upper()
        if status not in {"OK", "CAUTION", "REVIEW"}:
            raise ValueError("Guardrail review payload missing valid status")
        issues = data.get("issues", [])
        if not isinstance(issues, list):
            raise ValueError("Guardrail review payload missing issues list")
        issues_str = [str(issue) for issue in issues if str(issue).strip()]
        return {"status": status, "issues": issues_str}

    return await _with_llm_fallback(
        prompt=prompt,
        system=GUARDRAIL_REVIEW_SYSTEM_PROMPT,
        parse=_parse,
        stub=lambda: _deepcopy_stub(DEMO_GUARDRAIL_REVIEW),
        policy_block=policy_block,
    )
