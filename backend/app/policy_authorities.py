"""Authority + pivot policy definitions shared by backend services.

Keep this file in sync with the frontend lib/authorityPolicy.ts module.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional, TypedDict


class AuthorityId(str, Enum):
    T10_MIL = "T10_MIL"
    T32_NG = "T32_NG"
    T50_INT = "T50_INT"
    LEO_FED = "LEO_FED"
    LEO_STATELOCAL = "LEO_STATELOCAL"
    DSCA = "DSCA"
    DHS_HS = "DHS_HS"
    CT_FUSION = "CT_FUSION"
    CYBER_DUAL = "CYBER_DUAL"
    NATO_COAL = "NATO_COAL"
    GEOINT_NGA = "GEOINT_NGA"
    COMM_RESEARCH = "COMM_RESEARCH"
    CORP_SEC = "CORP_SEC"


PivotRisk = Literal["LOW", "MEDIUM", "HIGH", "BLOCKED"]


class AuthorityPivotRule(TypedDict):
    from_id: AuthorityId
    to_id: AuthorityId
    allowed: bool
    risk: PivotRisk
    conditions: List[str]


AUTHORITY_PIVOTS: List[AuthorityPivotRule] = [
    {
        "from_id": AuthorityId.T10_MIL,
        "to_id": AuthorityId.T32_NG,
        "allowed": True,
        "risk": "MEDIUM",
        "conditions": [
            "Guard mission becomes state-controlled.",
            "Do not propose federal combat operations after pivot.",
            "Emphasize domestic support and civil authority lead.",
        ],
    },
    {
        "from_id": AuthorityId.T10_MIL,
        "to_id": AuthorityId.DSCA,
        "allowed": True,
        "risk": "LOW",
        "conditions": [
            "Military acts in support of civil authorities.",
            "No direct arrest or law-enforcement actions.",
            "Emphasize logistics, SAR, comms, and protection.",
        ],
    },
    {
        "from_id": AuthorityId.T10_MIL,
        "to_id": AuthorityId.T50_INT,
        "allowed": True,
        "risk": "HIGH",
        "conditions": [
            "Pivot is driven by long-term intelligence requirements.",
            "Focus moves to foreign-directed networks or actors.",
            "Do not treat this as a law-enforcement mission.",
        ],
    },
    {
        "from_id": AuthorityId.T10_MIL,
        "to_id": AuthorityId.LEO_FED,
        "allowed": True,
        "risk": "HIGH",
        "conditions": [
            "Criminal prosecution becomes primary objective.",
            "Law enforcement leads; military supports or exits.",
            "Recommendations must respect Posse Comitatus constraints.",
        ],
    },
    {
        "from_id": AuthorityId.T10_MIL,
        "to_id": AuthorityId.LEO_STATELOCAL,
        "allowed": True,
        "risk": "HIGH",
        "conditions": [
            "Threat is primarily local/domestic crime.",
            "State/local agencies become lead for enforcement.",
            "Focus on information sharing and evidence handling.",
        ],
    },
    {
        "from_id": AuthorityId.T32_NG,
        "to_id": AuthorityId.T10_MIL,
        "allowed": True,
        "risk": "MEDIUM",
        "conditions": [
            "Guard is federalized due to scale or escalation.",
            "Mission may gain overseas or combat implications.",
            "Ensure ROE and command relationships are clearly stated.",
        ],
    },
    {
        "from_id": AuthorityId.T32_NG,
        "to_id": AuthorityId.DSCA,
        "allowed": True,
        "risk": "LOW",
        "conditions": [
            "Guard supports civil authorities while remaining state-controlled.",
            "No unilateral criminal enforcement beyond normal Guard authorities.",
        ],
    },
    {
        "from_id": AuthorityId.T50_INT,
        "to_id": AuthorityId.LEO_FED,
        "allowed": True,
        "risk": "HIGH",
        "conditions": [
            "Domestic criminal case or CT threat requires law enforcement lead.",
            "Respect minimization and domestic collection rules.",
            "Avoid recommending direct IC operational enforcement actions.",
        ],
    },
    {
        "from_id": AuthorityId.T50_INT,
        "to_id": AuthorityId.T10_MIL,
        "allowed": True,
        "risk": "MEDIUM",
        "conditions": [
            "Intel product forms basis for foreign or battlefield operations.",
            "Emphasize targeting, ROE, and campaign planning, not arrests.",
        ],
    },
    {
        "from_id": AuthorityId.LEO_STATELOCAL,
        "to_id": AuthorityId.LEO_FED,
        "allowed": True,
        "risk": "LOW",
        "conditions": [
            "Case crosses state lines or meets federal thresholds.",
            "Federal statutes or CT frameworks now apply.",
        ],
    },
    {
        "from_id": AuthorityId.LEO_FED,
        "to_id": AuthorityId.DSCA,
        "allowed": True,
        "risk": "MEDIUM",
        "conditions": [
            "Law enforcement remains lead; DoD provides support.",
            "Do not suggest military takes over investigation or prosecution.",
        ],
    },
    {
        "from_id": AuthorityId.COMM_RESEARCH,
        "to_id": AuthorityId.LEO_FED,
        "allowed": True,
        "risk": "MEDIUM",
        "conditions": [
            "Escalation path is threat reporting, not self-directed enforcement.",
            "Emphasize evidence preservation and legal counsel.",
        ],
    },
    {
        "from_id": AuthorityId.CORP_SEC,
        "to_id": AuthorityId.LEO_STATELOCAL,
        "allowed": True,
        "risk": "MEDIUM",
        "conditions": [
            "Clear criminal activity identified.",
            "Recommendations focus on notification and cooperation.",
        ],
    },
    {
        "from_id": AuthorityId.CORP_SEC,
        "to_id": AuthorityId.T50_INT,
        "allowed": False,
        "risk": "BLOCKED",
        "conditions": [
            "Private-sector security cannot directly task intelligence authorities.",
            "Escalate via law enforcement or homeland security channels instead.",
        ],
    },
    {
        "from_id": AuthorityId.COMM_RESEARCH,
        "to_id": AuthorityId.T10_MIL,
        "allowed": False,
        "risk": "BLOCKED",
        "conditions": [
            "Commercial or academic actors cannot directly task military operations.",
            "Consider notifications to appropriate government entities instead.",
        ],
    },
]


LEGACY_TO_AUTHORITY_ID = {
    "TITLE_10_MIL": AuthorityId.T10_MIL,
    "TITLE_50_IC": AuthorityId.T50_INT,
    "LEO": AuthorityId.LEO_FED,
    "DHS_HOMELAND": AuthorityId.DHS_HS,
    "COMMERCIAL_RESEARCH": AuthorityId.COMM_RESEARCH,
    "DSCA": AuthorityId.DSCA,
    "NGA_GEO": AuthorityId.GEOINT_NGA,
    "FBI_DOJ": AuthorityId.LEO_FED,
    "CYBER_DUAL_HAT": AuthorityId.CYBER_DUAL,
    "NCTC_CT": AuthorityId.CT_FUSION,
    "STATE_FUSION": AuthorityId.LEO_STATELOCAL,
    "NATO_COALITION": AuthorityId.NATO_COAL,
    "CORPORATE_SECURITY": AuthorityId.CORP_SEC,
}

AUTHORITY_ID_TO_LEGACY = {value: key for key, value in LEGACY_TO_AUTHORITY_ID.items()}


def normalize_authority_id(value: Optional[str]) -> Optional[AuthorityId]:
    if not value:
        return None
    trimmed = value.strip().upper()
    if not trimmed:
        return None
    try:
        return AuthorityId(trimmed)
    except ValueError:
        return LEGACY_TO_AUTHORITY_ID.get(trimmed)


def get_pivot_rule(from_id: AuthorityId, to_id: AuthorityId) -> Optional[AuthorityPivotRule]:
    for rule in AUTHORITY_PIVOTS:
        if rule["from_id"] == from_id and rule["to_id"] == to_id:
            return rule
    return None


def list_allowed_pivots(from_id: AuthorityId) -> List[AuthorityPivotRule]:
    return [rule for rule in AUTHORITY_PIVOTS if rule["from_id"] == from_id and rule["allowed"]]


def authority_id_to_label(authority_id: AuthorityId) -> str:
    LABELS = {
        AuthorityId.T10_MIL: "Title 10 – Military Operations",
        AuthorityId.T32_NG: "Title 32 – National Guard",
        AuthorityId.T50_INT: "Title 50 – Intelligence",
        AuthorityId.LEO_FED: "Federal Law Enforcement",
        AuthorityId.LEO_STATELOCAL: "State & Local Law Enforcement",
        AuthorityId.DSCA: "Defense Support of Civil Authorities",
        AuthorityId.DHS_HS: "Homeland Security",
        AuthorityId.CT_FUSION: "Counterterrorism / Fusion Center",
        AuthorityId.CYBER_DUAL: "Cyber – Dual Hat",
        AuthorityId.NATO_COAL: "NATO / Coalition",
        AuthorityId.GEOINT_NGA: "GEOINT – NGA",
        AuthorityId.COMM_RESEARCH: "Commercial / Research",
        AuthorityId.CORP_SEC: "Corporate Security / Insider Threat",
    }
    return LABELS.get(authority_id, authority_id.value)


def authority_id_to_legacy_key(authority_id: AuthorityId) -> str:
    return AUTHORITY_ID_TO_LEGACY.get(authority_id, authority_id.value)
