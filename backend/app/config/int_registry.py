"""Canonical INT taxonomy and helpers for APEX."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel


IntCode = Literal[
    "OSINT",
    "HUMINT",
    "SIGINT",
    "GEOINT",
    "MASINT",
    "CYBINT",
    "FININT",
    "TECHINT",
    "SOCMINT",
    "ALL_SOURCE",
    "LEO_CRIMINT",
    "CT_INT",
    "CI_INT",
]


class IntMetadata(BaseModel):
    code: IntCode
    label: str
    short_description: str
    typical_sources: List[str]
    typical_use_cases: List[str]
    legal_sensitivity_notes: str
    default_authorities: List[str]


INT_REGISTRY: List[IntMetadata] = [
    IntMetadata(
        code="OSINT",
        label="OSINT – Open-Source Intelligence",
        short_description="Intelligence derived from publicly or commercially available information.",
        typical_sources=[
            "News media and press releases",
            "Government public reports and filings",
            "Academic publications and think tank reports",
            "Public websites and online forums",
            "Commercial datasets and feeds",
        ],
        typical_use_cases=[
            "Pattern of life and background research",
            "Order of battle and capability assessments",
            "Threat environment baselining",
            "Narrative tracking and influence monitoring",
        ],
        legal_sensitivity_notes=(
            "Relies on publicly or commercially available information. Constraints focus on terms of service, "
            "privacy, and data protection laws, rather than classified handling rules. Still must avoid unlawful "
            "surveillance, harassment, or targeting of protected classes."
        ),
        default_authorities=[
            "TITLE_10_MIL",
            "TITLE_50_IC",
            "LEO",
            "DHS_HOMELAND",
            "COMMERCIAL_RESEARCH",
            "NATO_COALITION",
            "STATE_FUSION",
            "CORPORATE_SECURITY",
        ],
    ),
    IntMetadata(
        code="HUMINT",
        label="HUMINT – Human Intelligence",
        short_description="Intelligence derived from human sources through interviews, debriefs, or liaison.",
        typical_sources=[
            "Source meetings and debriefs",
            "Field reports and contact reports",
            "Debriefings of returning personnel",
            "Liaison reporting from partner organizations",
        ],
        typical_use_cases=[
            "Intent, motivation, and plans of actors",
            "Access to denied environments or closed groups",
            "Ground truth on local conditions",
            "Validating or refuting technical reporting",
        ],
        legal_sensitivity_notes=(
            "Often subject to strict rules on source handling, consent, and operations (e.g., Title 50 for intelligence "
            "activities, agency tradecraft policies, LEO interview and custodial rules, entrapment limits). Not "
            "appropriate for automated tasking of human sources without explicit human control."
        ),
        default_authorities=[
            "TITLE_50_IC",
            "TITLE_10_MIL",
            "LEO",
            "FBI_DOJ",
            "NCTC_CT",
            "STATE_FUSION",
        ],
    ),
    IntMetadata(
        code="SIGINT",
        label="SIGINT – Signals Intelligence",
        short_description="Intelligence derived from intercepted communications or electronic signals.",
        typical_sources=[
            "Communications intercepts (COMINT)",
            "Electronic emissions, radars, beacons (ELINT)",
            "Protocol- and network-layer telemetry",
            "Technical exploitation of RF and cyber systems",
        ],
        typical_use_cases=[
            "Network mapping and traffic characterization",
            "Emitter geolocation and pattern analysis",
            "Capability and readiness assessments",
            "Tipping and cueing for other INTs",
        ],
        legal_sensitivity_notes=(
            "Highly regulated due to privacy and surveillance concerns. Domestic collection, U.S. person data, and law "
            "enforcement use are governed by strict minimization rules, FISA authorities, and agency- or court-approved "
            "procedures. APEX should warn whenever a mission description suggests domestic intercepts or U.S. person content."
        ),
        default_authorities=[
            "TITLE_50_IC",
            "TITLE_10_MIL",
            "CYBER_DUAL_HAT",
            "NATO_COALITION",
        ],
    ),
    IntMetadata(
        code="GEOINT",
        label="GEOINT – Geospatial Intelligence",
        short_description="Intelligence derived from imagery, maps, and geospatial data.",
        typical_sources=[
            "Satellite and aerial imagery",
            "Commercial imagery services",
            "Digital elevation models and terrain data",
            "Foundation geospatial datasets and vector layers",
            "GPS logs and geotagged observations",
        ],
        typical_use_cases=[
            "Area of interest (AOI) characterization",
            "Facility mapping and pattern of life",
            "Line-of-sight and terrain analysis",
            "Change detection and damage assessment",
        ],
        legal_sensitivity_notes=(
            "Imagery and geospatial data can implicate privacy when focused on individuals, private property, or "
            "sensitive facilities. Constraints depend on collection platform and jurisdiction. Domestic targeting is often "
            "governed by additional policy and oversight."
        ),
        default_authorities=[
            "TITLE_10_MIL",
            "TITLE_50_IC",
            "NGA_GEO",
            "LEO",
            "DHS_HOMELAND",
            "NATO_COALITION",
            "STATE_FUSION",
        ],
    ),
    IntMetadata(
        code="MASINT",
        label="MASINT – Measurement & Signature Intelligence",
        short_description="Intelligence from technical measurements of physical phenomena (signatures).",
        typical_sources=[
            "Acoustic, seismic, or infrasound sensors",
            "Nuclear, chemical, or radiological detectors",
            "Spectral signatures and materials analysis",
            "Radar cross-section and telemetry",
        ],
        typical_use_cases=[
            "Weapons testing and characterization",
            "Detection of concealed or masked activity",
            "Environmental and hazard monitoring",
            "Attribution of unusual events or signatures",
        ],
        legal_sensitivity_notes=(
            "Typically focused on non-personal physical signatures, but may intersect with arms control treaties, "
            "environmental law, or hazardous material regulations. Human-targeted sensing in domestic environments raises "
            "privacy and legal concerns and should be flagged."
        ),
        default_authorities=[
            "TITLE_10_MIL",
            "TITLE_50_IC",
            "DHS_HOMELAND",
            "NCTC_CT",
            "NATO_COALITION",
        ],
    ),
    IntMetadata(
        code="CYBINT",
        label="CYBINT – Cyber / Network Intelligence",
        short_description="Intelligence focused on cyber terrain, network activity, and digital threats.",
        typical_sources=[
            "Network telemetry and flow data",
            "Endpoint security logs and alerts",
            "Threat intel feeds and malware sandboxes",
            "Dark web and underground forums (where lawfully accessed)",
        ],
        typical_use_cases=[
            "Threat actor tracking and campaign analysis",
            "Vulnerability and exposure assessments",
            "Defensive cyber operations support",
            "Attribution support for cyber incidents",
        ],
        legal_sensitivity_notes=(
            "Tied to computer crime statutes, privacy law, and rules for monitoring user activity. Offensive operations "
            "(exploits, active disruption) are highly authority-dependent and must be clearly distinguished from defensive "
            "monitoring and analysis."
        ),
        default_authorities=[
            "CYBER_DUAL_HAT",
            "TITLE_50_IC",
            "TITLE_10_MIL",
            "LEO",
            "FBI_DOJ",
            "DHS_HOMELAND",
            "CORPORATE_SECURITY",
        ],
    ),
    IntMetadata(
        code="FININT",
        label="FININT – Financial Intelligence",
        short_description="Intelligence derived from financial transactions, holdings, and flows of funds.",
        typical_sources=[
            "Banking and transaction records (where lawfully obtained)",
            "Sanctions and watchlist databases",
            "Corporate filings and ownership registries",
            "Suspicious activity reports (SARs) and CTRs",
        ],
        typical_use_cases=[
            "Tracing illicit finance and money laundering",
            "Sanctions and export control enforcement",
            "Threat finance and terrorism support analysis",
            "Network mapping via financial relationships",
        ],
        legal_sensitivity_notes=(
            "Contains highly sensitive personal and corporate financial data. Access normally requires specific legal "
            "authorities, subpoenas, warrants, or regulatory channels. Use in APEX scenarios should always be paired with "
            "explicit law enforcement or financial regulatory authorities."
        ),
        default_authorities=[
            "FBI_DOJ",
            "LEO",
            "NCTC_CT",
            "STATE_FUSION",
            "CORPORATE_SECURITY",
        ],
    ),
    IntMetadata(
        code="TECHINT",
        label="TECHINT – Technical Intelligence",
        short_description="Intelligence from exploitation and analysis of foreign materiel and systems.",
        typical_sources=[
            "Captured or acquired hardware and software",
            "Weapons systems and platforms",
            "Technical manuals and design documents",
            "Laboratory and reverse engineering reports",
        ],
        typical_use_cases=[
            "Understanding adversary capabilities and limitations",
            "Countermeasure development and survivability analysis",
            "Weapon and system performance assessments",
            "Support to acquisition and R&D decisions",
        ],
        legal_sensitivity_notes=(
            "Often governed by arms control, export control, and classification rules. Handling foreign materiel in "
            "domestic contexts may intersect with law enforcement and evidence handling rules."
        ),
        default_authorities=[
            "TITLE_10_MIL",
            "TITLE_50_IC",
            "NATO_COALITION",
        ],
    ),
    IntMetadata(
        code="SOCMINT",
        label="SOCMINT – Social Media Intelligence",
        short_description="Intelligence derived from social media platforms and online communities.",
        typical_sources=[
            "Public posts on major social platforms",
            "Messaging apps where access is lawfully obtained",
            "Online groups, forums, and comment threads",
            "Follower graphs and engagement metrics",
        ],
        typical_use_cases=[
            "Pattern of life and persona mapping",
            "Narrative analysis and influence tracking",
            "Event and protest monitoring",
            "Threat detection based on online indicators",
        ],
        legal_sensitivity_notes=(
            "Sits at the intersection of OSINT, privacy law, and speech protections. Targeting based on protected "
            "characteristics, mass monitoring without cause, or covert manipulation is highly sensitive and authority-"
            "dependent."
        ),
        default_authorities=[
            "TITLE_50_IC",
            "TITLE_10_MIL",
            "LEO",
            "DHS_HOMELAND",
            "STATE_FUSION",
            "COMMERCIAL_RESEARCH",
            "CORPORATE_SECURITY",
        ],
    ),
    IntMetadata(
        code="ALL_SOURCE",
        label="All-Source / Fusion",
        short_description="Integrated analysis that fuses multiple INTs into a single assessment.",
        typical_sources=[
            "Products and reports from multiple INT disciplines",
            "Partner and allied reporting",
            "Operational and open-source data",
            "Historical mission archives",
        ],
        typical_use_cases=[
            "High-level assessments for commanders or executives",
            "Target systems analysis and course-of-action comparisons",
            "Red team / blue team synthesis",
            "Decision support and risk trade-off analysis",
        ],
        legal_sensitivity_notes=(
            "Inherits the strictest handling rules from its inputs. All-source products must maintain provenance, "
            "caveats, and dissemination controls. Treat ALL_SOURCE as 'combined lanes', not a free pass to ignore "
            "individual INT constraints."
        ),
        default_authorities=[
            "TITLE_10_MIL",
            "TITLE_50_IC",
            "LEO",
            "DHS_HOMELAND",
            "NCTC_CT",
            "STATE_FUSION",
            "NATO_COALITION",
            "CORPORATE_SECURITY",
        ],
    ),
    IntMetadata(
        code="LEO_CRIMINT",
        label="LEO Crime Intelligence",
        short_description="Operational intelligence supporting investigations, patrol, and crime reduction.",
        typical_sources=[
            "Incident and arrest reports",
            "Records management and case files",
            "Jail and probation data",
            "Community tips and officer observations",
        ],
        typical_use_cases=[
            "Case pack preparation for prosecutors",
            "Hot spot and pattern analysis",
            "Link charts and association analysis",
            "Officer safety and warrant planning",
        ],
        legal_sensitivity_notes=(
            "Heavily constrained by criminal procedure, evidence rules, and civil rights protections. Use in domestic "
            "policing must respect probable cause standards, discovery, and limits on investigative techniques."
        ),
        default_authorities=[
            "LEO",
            "FBI_DOJ",
            "STATE_FUSION",
        ],
    ),
    IntMetadata(
        code="CT_INT",
        label="CT – Counterterrorism Intelligence",
        short_description="Multi-INT focus on preventing, disrupting, and responding to terrorism.",
        typical_sources=[
            "All-source IC reporting",
            "LEO case data and watchlists",
            "OSINT and SOCMINT on extremist networks",
            "Travel, border, and financial data (where authorized)",
        ],
        typical_use_cases=[
            "Threat stream triage and prioritization",
            "Target system and network analysis",
            "Attack surface and vulnerability mapping",
            "Threat assessments for venues and events",
        ],
        legal_sensitivity_notes=(
            "Very high sensitivity around U.S. person information, profiling, and use of bulk data. Governed by "
            "specialized CT frameworks, interagency agreements, and oversight mechanisms."
        ),
        default_authorities=[
            "NCTC_CT",
            "TITLE_50_IC",
            "LEO",
            "STATE_FUSION",
            "DHS_HOMELAND",
        ],
    ),
    IntMetadata(
        code="CI_INT",
        label="CI – Counterintelligence",
        short_description="Intelligence focused on detecting and mitigating espionage and insider threats.",
        typical_sources=[
            "Personnel and access records",
            "Security incident reports",
            "Insider threat monitoring data (where authorized)",
            "Foreign intelligence service reporting",
        ],
        typical_use_cases=[
            "Identifying recruitment and penetration efforts",
            "Protecting sensitive programs and facilities",
            "Insider threat detection and mitigation",
            "Risk assessment for foreign contact and travel",
        ],
        legal_sensitivity_notes=(
            "Touches employment law, privacy rules, and insider threat policy. Monitoring employees or contractors "
            "requires clear policy, notice, and appropriate legal foundations."
        ),
        default_authorities=[
            "TITLE_50_IC",
            "TITLE_10_MIL",
            "FBI_DOJ",
            "STATE_FUSION",
            "CORPORATE_SECURITY",
        ],
    ),
]


def get_int_registry() -> List[IntMetadata]:
    return INT_REGISTRY
