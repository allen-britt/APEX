"""Central definitions for mission authority lanes and guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Sequence


class AuthorityType(str, Enum):
    """Supported mission authority lanes for APEX."""

    TITLE_10_MIL = "TITLE_10_MIL"
    TITLE_50_IC = "TITLE_50_IC"
    LEO = "LEO"
    DHS_HOMELAND = "DHS_HOMELAND"
    COMMERCIAL_RESEARCH = "COMMERCIAL_RESEARCH"
    DSCA = "DSCA"
    NGA_GEO = "NGA_GEO"
    FBI_DOJ = "FBI_DOJ"
    CYBER_DUAL_HAT = "CYBER_DUAL_HAT"
    NCTC_CT = "NCTC_CT"
    STATE_FUSION = "STATE_FUSION"
    NATO_COALITION = "NATO_COALITION"
    CORPORATE_SECURITY = "CORPORATE_SECURITY"


@dataclass(frozen=True)
class AuthorityDescriptor:
    """Metadata and guardrail definitions per authority lane."""

    value: AuthorityType
    label: str
    description: str
    prompt_context: str
    prohibitions: str
    guardrail_keywords: Sequence[str]
    allowed_int_types: Sequence[str]
    ok_examples: Sequence[str]
    not_ok_examples: Sequence[str]


AUTHORITY_REGISTRY: Dict[AuthorityType, AuthorityDescriptor] = {
    AuthorityType.TITLE_10_MIL: AuthorityDescriptor(
        value=AuthorityType.TITLE_10_MIL,
        label="Title 10 – Military Operations",
        description=(
            "Operational ISR and mission analysis for military forces focused on foreign/battlefield threats."
        ),
        prompt_context=(
            "You are supporting Title 10 military operators. Emphasize operational planning, ISR, and effects"
            " while respecting civilian control."
        ),
        prohibitions=(
            "Do NOT recommend arrests, criminal prosecutions, or covert Title 50 tradecraft. Avoid domestic policing."
        ),
        guardrail_keywords=(
            "warrant",
            "arrest",
            "prosecute",
            "subpoena",
            "domestic surveillance",
        ),
        allowed_int_types=("OSINT", "GEOINT", "SIGINT", "HUMINT", "MASINT", "ALL_SOURCE"),
        ok_examples=(
            "Planning ISR coverage for an overseas target area",
            "Producing a battlespace intel brief for a deployed unit",
        ),
        not_ok_examples=(
            "Recommending military units arrest civilians inside CONUS",
            "Drafting domestic criminal case files as if they were law enforcement",
        ),
    ),
    AuthorityType.TITLE_50_IC: AuthorityDescriptor(
        value=AuthorityType.TITLE_50_IC,
        label="Title 50 – Intelligence",
        description=(
            "DIA-led HUMINT and counterintelligence production focused on foreign targets. Missions span OVERT "
            "(debriefings, interrogations, liaison, source operations) and CLANDESTINE (CLAN) collection, all in support "
            "of national, combatant command, and OSD priorities."
        ),
        prompt_context=(
            "You operate under Title 50 HUMINT authorities. Provide foreign intelligence assessments and collection "
            "insights grounded in overt or clandestine human reporting—never domestic law-enforcement narratives."
            " Reinforce operator intent, access, and tradecraft considerations without directing arrests or prosecutions."
        ),
        prohibitions=(
            "Do NOT recommend domestic arrests, warrant actions, or kinetic targeting orders. Keep outputs within "
            "intelligence production, liaison, and collection advisories—no criminal charging guidance."
        ),
        guardrail_keywords=(
            "arrest",
            "prosecute",
            "indict",
            "target package",
            "kinetic strike",
        ),
        allowed_int_types=("OSINT", "SIGINT", "HUMINT", "GEOINT", "MASINT", "CI"),
        ok_examples=(
            "Foreign adversary network mapping for strategic analysis",
            "Counterintelligence assessment on foreign influence operations",
        ),
        not_ok_examples=(
            "Suggesting bulk domestic surveillance of U.S. persons",
            "Planning law-enforcement-style arrest operations",
        ),
    ),
    AuthorityType.LEO: AuthorityDescriptor(
        value=AuthorityType.LEO,
        label="Law Enforcement",
        description="Criminal case work, evidence development, and investigative analysis.",
        prompt_context=(
            "You are supporting law-enforcement investigations. Discuss evidence, leads, and lawful process."
        ),
        prohibitions=(
            "Do NOT suggest illegal searches, bypassing warrants, or military operations."
        ),
        guardrail_keywords=(
            "kill chain",
            "air strike",
            "covert insertion",
            "signals collection overseas",
        ),
        allowed_int_types=("OSINT", "HUMINT", "GEOINT", "SIGINT", "CASE_INT"),
        ok_examples=(
            "Organizing leads for a burglary ring investigation",
            "Suggesting a lawful review of CCTV footage",
        ),
        not_ok_examples=(
            "Encouraging bypass of warrant requirements",
            "Telling officers to pull phone records without legal process",
        ),
    ),
    AuthorityType.DHS_HOMELAND: AuthorityDescriptor(
        value=AuthorityType.DHS_HOMELAND,
        label="DHS / Homeland Security",
        description="Border, transportation, and infrastructure security missions.",
        prompt_context=(
            "You are supporting DHS/fusion missions. Emphasize risk mitigation, protection, and preparedness."
        ),
        prohibitions=(
            "Do NOT direct military or law-enforcement actions outside DHS authority."
        ),
        guardrail_keywords=(
            "arrest",
            "kinetic",
            "offensive cyber",
            "extrajudicial",
        ),
        allowed_int_types=("OSINT", "GEOINT", "HUMINT", "SIGINT", "CT"),
        ok_examples=(
            "Risk assessment for ports of entry",
            "Pattern analysis of cross-border trafficking routes",
        ),
        not_ok_examples=(
            "Directing military operations outside remit",
            "Advising arbitrary mass surveillance",
        ),
    ),
    AuthorityType.COMMERCIAL_RESEARCH: AuthorityDescriptor(
        value=AuthorityType.COMMERCIAL_RESEARCH,
        label="Commercial / Research / Training",
        description="Corporate security, academic research, tabletop exercises (non-operational).",
        prompt_context=(
            "You are supporting training or research scenarios. Keep outputs defensive, analytic, and lawful."
        ),
        prohibitions=(
            "Do NOT suggest arrests, kinetic strikes, or illegal hacking."
        ),
        guardrail_keywords=(
            "exploit",
            "zero-day",
            "illegal access",
            "weaponize",
        ),
        allowed_int_types=("OSINT", "CORP_DATA", "SIMULATED"),
        ok_examples=(
            "Corporate insider threat risk scoring",
            "Academic analysis of public extremist propaganda",
        ),
        not_ok_examples=(
            "Directing real-world arrests",
            "Advising illegal hacking",
        ),
    ),
    AuthorityType.DSCA: AuthorityDescriptor(
        value=AuthorityType.DSCA,
        label="Defense Support of Civil Authorities",
        description="Military support to civil authorities during emergencies under civilian lead.",
        prompt_context=(
            "You are supporting DSCA missions—logistics, ISR, and analysis to aid civil authorities."
        ),
        prohibitions=(
            "Do NOT direct soldiers to conduct arrests or act as domestic police."
        ),
        guardrail_keywords=("arrest", "detain", "search", "seize evidence"),
        allowed_int_types=("OSINT", "GEOINT", "SIGINT", "LOGISTICS"),
        ok_examples=("Mapping flood damage", "Suggesting ISR coverage to locate survivors"),
        not_ok_examples=("Ordering troops to arrest civilians", "Directing criminal investigations"),
    ),
    AuthorityType.NGA_GEO: AuthorityDescriptor(
        value=AuthorityType.NGA_GEO,
        label="GEOINT – NGA",
        description="Geospatial imaging and mapping to support national security decisions.",
        prompt_context=(
            "You are providing GEOINT insights. Focus on terrain, infrastructure, and non-PII analysis."
        ),
        prohibitions=(
            "Do NOT propose persistent tracking of U.S. persons without legal basis."
        ),
        guardrail_keywords=("track individual", "personally identifiable", "target citizen"),
        allowed_int_types=("GEOINT", "OSINT", "MAP_DATA", "SIGINT_OVERLAY"),
        ok_examples=("AOI overlays showing threat patterns", "Deriving terrain insights"),
        not_ok_examples=("Persistent individualized tracking of U.S. persons"),
    ),
    AuthorityType.FBI_DOJ: AuthorityDescriptor(
        value=AuthorityType.FBI_DOJ,
        label="Federal Investigative – DOJ/FBI",
        description="Federal criminal and national security investigations under DOJ authorities.",
        prompt_context=(
            "You are supporting DOJ/FBI investigations. Focus on evidence, legal process, and case building."
        ),
        prohibitions=(
            "Do NOT encourage surveillance or searches outside warrants or statutes."
        ),
        guardrail_keywords=("warrantless", "tamper evidence", "coerce"),
        allowed_int_types=("OSINT", "HUMINT", "SIGINT", "GEOINT", "ALL_SOURCE"),
        ok_examples=("Structuring a federal case pack", "Suggesting MLAT requests"),
        not_ok_examples=("Proposing surveillance outside scope", "Encouraging evidence tampering"),
    ),
    AuthorityType.CYBER_DUAL_HAT: AuthorityDescriptor(
        value=AuthorityType.CYBER_DUAL_HAT,
        label="Cyber – Dual-Hat",
        description="Joint cyber missions where intelligence (NSA) and operational (CYBERCOM) roles intersect.",
        prompt_context=(
            "You are supporting dual-hat cyber missions. Keep roles separated and respect approvals."
        ),
        prohibitions=(
            "Do NOT recommend unauthorized offensive hacks or mixing data into domestic contexts."
        ),
        guardrail_keywords=("unauthorized exploit", "hack back"),
        allowed_int_types=("SIGINT", "OSINT", "TECH_TELEMETRY", "MALWARE_INT"),
        ok_examples=("Mapping adversary C2 infrastructure", "Recommending defensive posture"),
        not_ok_examples=("Recommending unauthorized offensive hacks"),
    ),
    AuthorityType.NCTC_CT: AuthorityDescriptor(
        value=AuthorityType.NCTC_CT,
        label="Counterterrorism Fusion",
        description="Integrative terrorism-related analysis across agencies (NCTC-style).",
        prompt_context=(
            "You are providing CT fusion analysis. Combine data responsibly and protect civil liberties."
        ),
        prohibitions=(
            "Do NOT treat broad populations as suspects without basis or design mass surveillance schemes."
        ),
        guardrail_keywords=("mass surveillance", "profiling"),
        allowed_int_types=("OSINT", "SIGINT", "HUMINT", "GEOINT", "LEO_REPORTS"),
        ok_examples=("All-source threat overview", "Risk scoring for CT threats"),
        not_ok_examples=("Treating entire communities as suspects"),
    ),
    AuthorityType.STATE_FUSION: AuthorityDescriptor(
        value=AuthorityType.STATE_FUSION,
        label="State / Regional Fusion",
        description="State-level centers combining intel and law enforcement reporting.",
        prompt_context=(
            "You are supporting a state fusion center. Balance sharing with privacy protections."
        ),
        prohibitions=(
            "Do NOT encourage profiling based on protected classes or indiscriminate collection."
        ),
        guardrail_keywords=("profiling", "indiscriminate"),
        allowed_int_types=("OSINT", "LEO_REPORTS", "HUMINT", "DHS_INT"),
        ok_examples=("Crime trend analysis", "Integrating local tips and federal warnings"),
        not_ok_examples=("Encouraging profiling based on protected characteristics"),
    ),
    AuthorityType.NATO_COALITION: AuthorityDescriptor(
        value=AuthorityType.NATO_COALITION,
        label="NATO / Coalition",
        description="Multinational operations and intelligence sharing with releasability caveats.",
        prompt_context=(
            "You are supporting coalition missions. Respect national caveats and releasability rules."
        ),
        prohibitions=(
            "Do NOT mix NOFORN intel into coalition products or violate caveats."
        ),
        guardrail_keywords=("NOFORN", "unauthorized release"),
        allowed_int_types=("OSINT", "GEOINT", "SIGINT", "HUMINT"),
        ok_examples=("Coalition threat picture from releasable sources"),
        not_ok_examples=("Sharing data contrary to caveats"),
    ),
    AuthorityType.CORPORATE_SECURITY: AuthorityDescriptor(
        value=AuthorityType.CORPORATE_SECURITY,
        label="Corporate Security / Insider Threat",
        description="Commercial physical/cyber security, employee risk, fraud detection.",
        prompt_context=(
            "You are supporting corporate security. Respect labor law, privacy, and policy boundaries."
        ),
        prohibitions=(
            "Do NOT advise unlawful monitoring, wiretaps, or privacy violations."
        ),
        guardrail_keywords=("wiretap", "spy on employee", "illegal surveillance"),
        allowed_int_types=("OSINT", "CORP_DATA", "HR_DATA", "RISK_SCORING"),
        ok_examples=("Insider threat alerts based on corporate policy"),
        not_ok_examples=("Encouraging unlawful wiretaps"),
    ),
}


def normalize_authority(
    value: str | AuthorityType | None,
    *,
    default: AuthorityType | None = AuthorityType.LEO,
) -> AuthorityType | None:
    """Resolve arbitrary user-provided value into a supported authority type."""

    if isinstance(value, AuthorityType):
        return value
    if isinstance(value, str):
        cleaned = value.strip().upper()
        for authority in AuthorityType:
            if authority.value == cleaned:
                return authority
        legacy_map = {
            "TITLE10": AuthorityType.TITLE_10_MIL,
            "TITLE50": AuthorityType.TITLE_50_IC,
            "CIVILIAN": AuthorityType.COMMERCIAL_RESEARCH,
            "JOINT": AuthorityType.TITLE_50_IC,
        }
        if cleaned in legacy_map:
            return legacy_map[cleaned]
    return default


def get_descriptor(value: str | AuthorityType | None) -> AuthorityDescriptor:
    authority = normalize_authority(value)
    if authority is None:
        raise ValueError("Unknown authority descriptor")
    return AUTHORITY_REGISTRY[authority]


def try_get_descriptor(value: str | AuthorityType | None) -> AuthorityDescriptor | None:
    authority = normalize_authority(value, default=None)
    if authority is None:
        return None
    return AUTHORITY_REGISTRY[authority]


def authority_prompt_block(value: str | AuthorityType | None) -> str:
    """Return a reusable prompt snippet describing the authority lane."""

    descriptor = get_descriptor(value)
    return (
        f"Authority Lane: {descriptor.label} ({descriptor.value.value})\n"
        f"Context: {descriptor.prompt_context}\n"
        f"Prohibitions: {descriptor.prohibitions}\n"
        f"Do Examples: {', '.join(descriptor.ok_examples[:2])}\n"
        f"Don't Examples: {', '.join(descriptor.not_ok_examples[:2])}"
    )


def guardrail_keywords(value: str | AuthorityType | None) -> Sequence[str]:
    return get_descriptor(value).guardrail_keywords


def redact_out_of_scope_content(value: str | AuthorityType | None, text: str) -> tuple[str, List[str]]:
    """Simple heuristic guardrail pass over LLM output."""

    descriptor = get_descriptor(value)
    lower_text = text.lower()
    hits: List[str] = []
    sanitized = text
    for keyword in descriptor.guardrail_keywords:
        lower_keyword = keyword.lower()
        if lower_keyword in lower_text:
            hits.append(keyword)
            sanitized = sanitized.replace(keyword, "[REDACTED]")
            sanitized = sanitized.replace(keyword.upper(), "[REDACTED]")
    return sanitized, hits


def format_guardrail_note(authority: str | AuthorityType | None, violations: Iterable[str]) -> str:
    descriptor = get_descriptor(authority)
    violations_text = ", ".join(sorted({violation for violation in violations}))
    return (
        f"Note: Some requested content was outside the {descriptor.label} lane."
        f" The response has been limited to allowed scope (flagged: {violations_text})."
    )
