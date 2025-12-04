from __future__ import annotations

from typing import List, Literal, Optional, TypedDict

HumintTemplateId = Literal[
    "HUMINT_IIR_STANDARD",
    "HUMINT_IIR_TACTICAL_SPOT",
    "HUMINT_DEBRIEF_SUMMARY",
    "HUMINT_SOURCE_CONTACT",
    "HUMINT_SOURCE_VALIDATION",
    "HUMINT_LEAD_SHEET",
]


class HumintSectionDefinition(TypedDict):
    id: str
    label: str
    kind: Literal[
        "header",
        "bluf",
        "summary",
        "narrative",
        "analysis",
        "recommendations",
        "evaluation",
        "administrative",
    ]
    required: bool
    multiParagraph: bool
    aiRoleHint: Optional[str]


class HumintTemplateDefinition(TypedDict):
    id: HumintTemplateId
    name: str
    description: str
    sections: List[HumintSectionDefinition]


HUMINT_IIR_STANDARD: HumintTemplateDefinition = {
    "id": "HUMINT_IIR_STANDARD",
    "name": "HUMINT Intelligence Information Report",
    "description": "Baseline IIR aligned with FM 101-5-2 formatting for Army, DIA, and Joint HUMINT dissemination.",
    "sections": [
        {
            "id": "header",
            "label": "Report Header",
            "kind": "header",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Populate DTG, serials, and classification exactly as provided; never fabricate control numbers.",
        },
        {
            "id": "bluf",
            "label": "Bottom Line Up Front",
            "kind": "bluf",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Summarize the most critical HUMINT insight in <=3 sentences citing source reliability and confidence.",
        },
        {
            "id": "summary",
            "label": "Collection Summary",
            "kind": "summary",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Outline collection circumstances, time, location, and participants without analysis.",
        },
        {
            "id": "narrative",
            "label": "Detailed Narrative",
            "kind": "narrative",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Present the source reporting verbatim or paraphrased with timestamps and provenance markers.",
        },
        {
            "id": "analysis",
            "label": "Analyst Comments",
            "kind": "analysis",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Differentiate analytic judgements from raw source data and cite corroborating KG references.",
        },
        {
            "id": "recommendations",
            "label": "Recommended Follow-Up",
            "kind": "recommendations",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "List collection questions, verification tasks, and handling notes tied to cited sections.",
        },
        {
            "id": "administrative",
            "label": "Administrative Data",
            "kind": "administrative",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Record source identifying numbers, eval codes, and HUMINT control data exactly as provided.",
        },
    ],
}

HUMINT_IIR_TACTICAL_SPOT: HumintTemplateDefinition = {
    "id": "HUMINT_IIR_TACTICAL_SPOT",
    "name": "Tactical Spot Report",
    "description": "Rapid HUMINT spot report for time-sensitive tactical dissemination.",
    "sections": [
        {
            "id": "header",
            "label": "Spot Header",
            "kind": "header",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Include DTG, grid, unit, and priority handling instructions only from source text.",
        },
        {
            "id": "bluf",
            "label": "Critical Observation",
            "kind": "bluf",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "State the tactical observation in one sentence referencing source reliability.",
        },
        {
            "id": "narrative",
            "label": "Observation Narrative",
            "kind": "narrative",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Describe what the source observed with time, place, and actors, no extrapolation.",
        },
        {
            "id": "analysis",
            "label": "Immediate Assessment",
            "kind": "analysis",
            "required": False,
            "multiParagraph": False,
            "aiRoleHint": "Offer concise assessment referencing doctrine triggers; leave empty if unsupported.",
        },
        {
            "id": "recommendations",
            "label": "Immediate Actions",
            "kind": "recommendations",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Provide 2-3 immediate questions or verifications operators can execute now.",
        },
    ],
}

HUMINT_DEBRIEF_SUMMARY: HumintTemplateDefinition = {
    "id": "HUMINT_DEBRIEF_SUMMARY",
    "name": "HUMINT Debrief Summary",
    "description": "Structured summary of post-mission source debriefs.",
    "sections": [
        {
            "id": "header",
            "label": "Debrief Header",
            "kind": "header",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Capture session ID, date, debriefer, interpreter, and location as provided.",
        },
        {
            "id": "summary",
            "label": "Session Overview",
            "kind": "summary",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Summarize objectives, rapport, and overall source demeanor.",
        },
        {
            "id": "narrative",
            "label": "Key Reporting",
            "kind": "narrative",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "List major points chronologically with question-response pairing.",
        },
        {
            "id": "analysis",
            "label": "Analyst Assessment",
            "kind": "analysis",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Assess reliability, motivations, and alignment with existing holdings.",
        },
        {
            "id": "gaps",
            "label": "Identified Gaps",
            "kind": "analysis",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Enumerate unanswered questions or inconsistencies referencing prior sections.",
        },
        {
            "id": "recommendations",
            "label": "Next Session Plan",
            "kind": "recommendations",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Provide prioritized question lines, verification tasks, and rapport considerations.",
        },
    ],
}

HUMINT_SOURCE_CONTACT: HumintTemplateDefinition = {
    "id": "HUMINT_SOURCE_CONTACT",
    "name": "Source Contact Report",
    "description": "Record of routine contact meetings with registered sources.",
    "sections": [
        {
            "id": "header",
            "label": "Contact Header",
            "kind": "header",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Document contact date, control number, location, and handlers.",
        },
        {
            "id": "summary",
            "label": "Engagement Summary",
            "kind": "summary",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Describe purpose of contact, duration, and atmospherics in 2-3 sentences.",
        },
        {
            "id": "narrative",
            "label": "Reporting",
            "kind": "narrative",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Capture source statements with attribution tags and time references.",
        },
        {
            "id": "analysis",
            "label": "Handler Notes",
            "kind": "analysis",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Assess source credibility, mood, and operational readiness referencing prior contacts.",
        },
        {
            "id": "recommendations",
            "label": "Handling Guidance",
            "kind": "recommendations",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "List rapport-building steps, incentive adjustments, and immediate follow-ups.",
        },
        {
            "id": "administrative",
            "label": "Control Data",
            "kind": "administrative",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Record payment data, cover arrangements, and comm windows exactly as provided.",
        },
    ],
}

HUMINT_SOURCE_VALIDATION: HumintTemplateDefinition = {
    "id": "HUMINT_SOURCE_VALIDATION",
    "name": "Source Validation Worksheet",
    "description": "Structured evaluation of HUMINT source reliability and placement-access.",
    "sections": [
        {
            "id": "header",
            "label": "Validation Header",
            "kind": "header",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Include source identifier, sponsoring unit, and validation phase markers.",
        },
        {
            "id": "summary",
            "label": "Placement & Access",
            "kind": "summary",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Summarize how the source accesses the reported information with explicit examples.",
        },
        {
            "id": "analysis",
            "label": "Reliability Assessment",
            "kind": "analysis",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Score historical accuracy, motivation, and any deception indicators referencing KG corroboration.",
        },
        {
            "id": "narrative",
            "label": "Reporting History",
            "kind": "narrative",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "List key prior reports with outcomes and validation status.",
        },
        {
            "id": "recommendations",
            "label": "Validation Actions",
            "kind": "recommendations",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Describe checks, surveillance, or corroboration tasks needed before certification.",
        },
        {
            "id": "evaluation",
            "label": "Final Evaluation",
            "kind": "evaluation",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Provide disposition (retain, suspend, terminate) with justification referencing sections.",
        },
    ],
}

HUMINT_LEAD_SHEET: HumintTemplateDefinition = {
    "id": "HUMINT_LEAD_SHEET",
    "name": "HUMINT Lead Sheet",
    "description": "Template for recording actionable leads derived from HUMINT reporting for cross-cueing.",
    "sections": [
        {
            "id": "header",
            "label": "Lead Header",
            "kind": "header",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Capture lead ID, originating report, and classification per doctrine.",
        },
        {
            "id": "summary",
            "label": "Lead Overview",
            "kind": "summary",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Summarize the lead, threat, or opportunity in <=2 sentences referencing the source section.",
        },
        {
            "id": "narrative",
            "label": "Supporting Details",
            "kind": "narrative",
            "required": True,
            "multiParagraph": True,
            "aiRoleHint": "Document specifics (names, locations, times, capabilities) tied to provenance.",
        },
        {
            "id": "analysis",
            "label": "Analytic Context",
            "kind": "analysis",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Describe how the lead aligns/conflicts with KG holdings and mission objectives.",
        },
        {
            "id": "recommendations",
            "label": "Action Items",
            "kind": "recommendations",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "Enumerate verification tasks and cross-INT cueing opportunities referencing KG nodes.",
        },
        {
            "id": "administrative",
            "label": "Routing & Dissemination",
            "kind": "administrative",
            "required": True,
            "multiParagraph": False,
            "aiRoleHint": "List distribution, suspense dates, and caveats exactly as directed by doctrine.",
        },
    ],
}

HUMINT_TEMPLATES: List[HumintTemplateDefinition] = [
    HUMINT_IIR_STANDARD,
    HUMINT_IIR_TACTICAL_SPOT,
    HUMINT_DEBRIEF_SUMMARY,
    HUMINT_SOURCE_CONTACT,
    HUMINT_SOURCE_VALIDATION,
    HUMINT_LEAD_SHEET,
]
