from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field

from app.authorities import AuthorityType

LEO_CASE_SUMMARY_MARKDOWN = """# LEO CASE SUMMARY – {{ mission_name }}

**Mission:** {{ mission_name }}  
**Authority:** {{ mission_authority }}  
**INT Lanes:** {{ mission_int_lanes }}  
**Prepared by:** {{ prepared_by }}  
**Date:** {{ report_date }}

---

## 1. Key Judgments

- (KJ1) ____________________  
  - Confidence: HIGH / MEDIUM / LOW  
  - Evidence Source: ____________________
- (KJ2) ____________________  
  - Confidence: HIGH / MEDIUM / LOW  
  - Evidence Source: ____________________
- (KJ3) ____________________  
  - Confidence: HIGH / MEDIUM / LOW  
  - Evidence Source: ____________________

---

## 2. Incident Overview

### 2.1 Confirmed Incidents

| Date/Time | Location | Summary | Evidence Source |
|-----------|----------|---------|-----------------|
| {{ incidents | default("None available") }} |

### 2.2 Patterns

- Describe recurring locations, times, targets, or behaviors. If none, state: "No discernible pattern based on current incidents."

---

## 3. Subjects & Associates

### 3.1 Primary Subjects

| Name | Type | Role | Evidence Basis |
|------|------|------|----------------|
| {{ subjects | default("None identified") }} |

### 3.2 Associates / Linked Identities

- Summarize linked individuals, handles, vehicles, or organizations. If none, state: "No associates or linked identities identified in current data."

---

## 4. Modus Operandi

- Describe entry/exit methods, targeting logic, get-away, and resale behavior. If insufficient evidence exists, note the gaps explicitly.

---

## 5. Evidence & Corroboration

### 5.1 OSINT
- Key handles, posts, or items and how they corroborate other sources.

### 5.2 FININT
- Relevant transactions, amounts, or patterns tied to proceeds of crime.

### 5.3 CCTV / Physical
- Visual evidence (suspects, vehicles, behaviors) with locations and dates.

### 5.4 Other
- Witness statements, reports, or additional records.

### 5.5 Evidence Assessment
- Summarize what is strongly supported, weakly supported, or speculative.

---

## 6. Gaps & Constraints

- List specific intelligence gaps (e.g., "No positive IDs", "Vehicle data incomplete").
- List constraints (jurisdiction, authority, missing warrants, etc.).

---

## 7. Recommended Actions (LEO)

- For each action, specify Priority (P1 immediate / P2 near-term / P3 long-term), the description, which gap it addresses, and the indicator of success.

---

## 8. Risk & Civil Liberties Considerations

- Describe privacy/civil-liberties risks for the recommended actions (e.g., ALPR, CCTV, OSINT, financial subpoenas) and note any warrants or specific legal process required.
"""

OSINT_POL_LEO_MARKDOWN = """# OSINT PATTERN OF LIFE – {{subject_display_name}}

**Classification:** UNCLASSIFIED // TRAINING USE ONLY  
**Authority:** [Simulation / Training]  
**Case ID:** {{case_id}}  
**Mission:** {{mission_title}}  
**Mission Authority Lane:** {{authority_label}}  
**INT Lane:** OSINT – Open Source  
**Prepared by:** {{analyst_name}}  
**Date:** {{report_date}}

---

## 1. Executive Summary

{{bluf_paragraph}}

---

## 2. Subject Identifiers & Accounts

- **Legal name(s):** {{names_list}}
- **Usernames / handles:** {{handles_list}}
- **Known emails / phones:** {{contact_list}}
- **Profile URLs:**  
  {{profile_urls_bullets}}

---

## 3. Platform Activity Overview

{{platform_activity_summary}}

---

## 4. Temporal & Spatial Patterns

- **Typical activity windows:** {{activity_windows}}
- **Locations referenced / geotagged:** {{locations_brief}}

Narrative:

{{temporal_spatial_narrative}}

---

## 5. Network & Affiliations

{{network_affiliations_summary}}

---

## 6. Behavioral Indicators

{{behavioral_indicators}}

---

## 7. Gaps & Confidence

- **Key gaps:**  
  {{gaps_list}}

- **Analyst confidence:** {{confidence_level}} ({{confidence_rationale}})

---

## 8. Recommended Next Steps (OSINT / LEO-safe)

_Frame next steps as intelligence recommendations or referrals (e.g., "Coordinate with appropriate law-enforcement partners through established legal channels to..."). Do **not** direct arrests, traffic stops, weapon seizures, or other enforcement actions._

{{recommended_next_steps}}
"""

FULL_INTREP_MARKDOWN = """# INTELLIGENCE REPORT – {{mission_title}}

**Classification:** UNCLASSIFIED // TRAINING USE ONLY  
**Authority:** [Simulation / Training]  
**Mission ID:** {{mission_id}}  
**Mission Authority Lane:** {{authority_label}}  
**INT Lanes:** {{int_lanes}}  
**Prepared by:** {{analyst_name}}  
**Date:** {{report_date}}

---

## 1. Executive Summary

{{bluf_paragraph}}

---

## 2. Situation & Context

{{situation_context}}

---

## 3. Intelligence Picture

{{intelligence_picture}}

---

## 4. Assessment & Judgments

{{assessment_body}}

- **Overall confidence:** {{confidence_level}} ({{confidence_rationale}})

---

## 5. Courses of Action (High-Level)

_Offer analytic recommendations using coordination/referral phrasing (e.g., "Recommend that host-nation law enforcement consider…"). Avoid direct orders to arrest, seize, or conduct traffic stops._

{{coas_high_level}}

---

## 6. Gaps & Collection Recommendations

{{gaps_and_collection}}

---

## 7. Risks

{{risks_section}}
"""

DELTA_UPDATE_MARKDOWN = """# DELTA UPDATE – {{mission_title}}

**Classification:** UNCLASSIFIED // TRAINING USE ONLY  
**Authority:** [Simulation / Training]  
**Case ID:** {{case_id}}  
**Compared to:** {{prior_report_timestamp}}  
**Generated:** {{report_date}}  

---

## 1. Executive Summary (Changes Only)

{{delta_bluf}}

---

## 2. New or Changed Facts

{{new_facts_list}}

---

## 3. Updated Assessments

{{updated_assessments}}

---

## 4. Updated Gaps

{{updated_gaps}}

---

## 5. Updated Recommended Actions

_Express actions as intelligence referrals/coordination steps (e.g., "Refer findings to competent authorities...") and do not direct arrests, traffic stops, or seizures._

{{updated_actions}}
"""


class TemplateDefinitionNotFound(Exception):
    """Raised when a template definition is missing."""


class InternalReportTemplate(BaseModel):
    id: str
    label: str
    description: str
    markdown_skeleton: str
    authority_scope: Literal["leo", "ic", "joint"]
    int_type: str = "ALL_SOURCE"
    mission_domains: List[str] = Field(default_factory=list)
    int_lanes_allowed: List[str] = Field(default_factory=list)
    allowed_authorities: List[str] = Field(default_factory=list)
    allowed_int_types: List[str] = Field(default_factory=list)
    int_types: List[str] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)
    uses_decision_dataset: bool = False
    title10_allowed: bool = False
    title50_allowed: bool = False

    @property
    def name(self) -> str:
        return self.label
class TemplateService:
    """Simple in-memory template registry.

    TODO: Move template definitions to JSON/YAML once the schema stabilizes.
    """

    def __init__(self) -> None:
        self._templates: Dict[str, InternalReportTemplate] = {
            template.id: template for template in self._load_default_templates()
        }

    def list_templates(self) -> List[InternalReportTemplate]:
        return list(self._templates.values())

    def get_template(self, template_id: str) -> InternalReportTemplate:
        template = self._templates.get(template_id)
        if not template:
            raise TemplateDefinitionNotFound(f"Unknown template id: {template_id}")
        return template

    def _load_default_templates(self) -> List[InternalReportTemplate]:
        return [
            InternalReportTemplate(
                id="leo_case_summary_v1",
                label="LEO Case Summary",
                description="Structured law-enforcement case narrative with evidence, gaps, and actions.",
                markdown_skeleton=LEO_CASE_SUMMARY_MARKDOWN,
                authority_scope="leo",
                int_type="CASE_INT",
                mission_domains=["LEO"],
                int_lanes_allowed=["CASE_INT", "OSINT", "HUMINT", "GEOINT", "SIGINT"],
                allowed_authorities=[AuthorityType.LEO.value],
                sections=[
                    "Executive Summary",
                    "Incident Overview",
                    "Subjects & Associates",
                    "Modus Operandi",
                    "Evidence & Corroboration",
                    "Gaps & Constraints",
                    "Recommended Actions",
                    "Risk & Civil Liberties",
                ],
            ),
            InternalReportTemplate(
                id="osint_pattern_of_life_leo_v1",
                label="OSINT Pattern of Life (LEO)",
                description="OSINT-focused behavioral and identity brief tailored for law enforcement.",
                markdown_skeleton=OSINT_POL_LEO_MARKDOWN,
                authority_scope="leo",
                int_type="OSINT",
                mission_domains=["LEO"],
                int_lanes_allowed=["OSINT", "SOCMINT"],
                allowed_authorities=[AuthorityType.LEO.value, AuthorityType.DHS_HOMELAND.value],
                sections=[
                    "Executive Summary",
                    "Subject Identifiers",
                    "Platform Activity",
                    "Temporal & Spatial Patterns",
                    "Network & Affiliations",
                    "Behavioral Indicators",
                    "Gaps & Confidence",
                    "Recommended Next Steps",
                ],
            ),
            InternalReportTemplate(
                id="full_intrep_v1",
                label="Full INTREP",
                description="All-source intelligence report for joint or interagency consumers.",
                markdown_skeleton=FULL_INTREP_MARKDOWN,
                authority_scope="joint",
                int_type="ALL_SOURCE",
                mission_domains=["Joint"],
                int_lanes_allowed=["ALL_SOURCE", "OSINT", "HUMINT", "GEOINT", "SIGINT"],
                allowed_authorities=[
                    AuthorityType.TITLE_10_MIL.value,
                    AuthorityType.TITLE_50_IC.value,
                    AuthorityType.LEO.value,
                    AuthorityType.DHS_HOMELAND.value,
                ],
                title10_allowed=True,
                title50_allowed=True,
                sections=[
                    "Executive Summary",
                    "Situation & Context",
                    "Intelligence Picture",
                    "Assessment & Judgments",
                    "Courses of Action",
                    "Gaps & Collection",
                    "Risks",
                ],
            ),
            InternalReportTemplate(
                id="delta_update_v1",
                label="Delta Update",
                description="Change log highlighting what shifted since the last approved product.",
                markdown_skeleton=DELTA_UPDATE_MARKDOWN,
                authority_scope="joint",
                int_type="ALL_SOURCE",
                mission_domains=["Joint"],
                int_lanes_allowed=["ALL_SOURCE", "OSINT", "HUMINT", "GEOINT", "SIGINT"],
                allowed_authorities=[
                    AuthorityType.TITLE_10_MIL.value,
                    AuthorityType.TITLE_50_IC.value,
                    AuthorityType.LEO.value,
                    AuthorityType.DSCA.value,
                ],
                title10_allowed=True,
                title50_allowed=True,
                sections=[
                    "Executive Summary",
                    "New or Changed Facts",
                    "Updated Assessments",
                    "Updated Gaps",
                    "Updated Recommended Actions",
                ],
            ),
            InternalReportTemplate(
                id="commander_decision_sheet_v1",
                label="Commander Decision Sheet",
                description="Decision-focused layout leveraging the structured DecisionDataset output.",
                markdown_skeleton="",
                authority_scope="joint",
                int_type="ALL_SOURCE",
                mission_domains=["Joint"],
                int_lanes_allowed=["ALL_SOURCE"],
                allowed_authorities=[
                    AuthorityType.TITLE_10_MIL.value,
                    AuthorityType.TITLE_50_IC.value,
                    AuthorityType.NATO_COALITION.value,
                ],
                title10_allowed=True,
                title50_allowed=True,
                uses_decision_dataset=True,
                sections=[
                    "Mission Overview",
                    "Decisions",
                    "Courses of Action",
                    "Policy & Blind Spots",
                ],
            ),
        ]
