// Authority and pivot policy definitions used across the frontend.
// IMPORTANT: Treat this file as the ground truth list of authorities and pivot rules.
// Keep the backend mirror (app/policy_authorities.py) in sync whenever you update this file.

export type AuthorityId =
  | "T10_MIL"
  | "T32_NG"
  | "T50_INT"
  | "LEO_FED"
  | "LEO_STATELOCAL"
  | "DSCA"
  | "DHS_HS"
  | "CT_FUSION"
  | "CYBER_DUAL"
  | "NATO_COAL"
  | "GEOINT_NGA"
  | "COMM_RESEARCH"
  | "CORP_SEC";

export interface AuthorityMeta {
  id: AuthorityId;
  label: string;
  category: "MIL" | "INT" | "LEO" | "CIV" | "COALITION";
  description: string;
}

export const AUTHORITIES: Record<AuthorityId, AuthorityMeta> = {
  T10_MIL: {
    id: "T10_MIL",
    label: "Title 10 – Military Operations",
    category: "MIL",
    description:
      "Federal active-duty military operations. Foreign/battlefield focus; limited role inside the U.S."
  },
  T32_NG: {
    id: "T32_NG",
    label: "Title 32 – National Guard",
    category: "MIL",
    description:
      "State-controlled, federally funded National Guard activities. Often domestic support."
  },
  T50_INT: {
    id: "T50_INT",
    label: "Title 50 – Intelligence",
    category: "INT",
    description:
      "U.S. intelligence community authorities; foreign intelligence and certain counterterrorism missions."
  },
  LEO_FED: {
    id: "LEO_FED",
    label: "Federal Law Enforcement",
    category: "LEO",
    description:
      "Federal law enforcement (e.g., FBI, DHS/HSI, DEA). Criminal investigations, CT at federal level."
  },
  LEO_STATELOCAL: {
    id: "LEO_STATELOCAL",
    label: "State & Local Law Enforcement",
    category: "LEO",
    description:
      "State, county, and municipal police/sheriff agencies with local criminal authority."
  },
  DSCA: {
    id: "DSCA",
    label: "Defense Support of Civil Authorities (DSCA)",
    category: "MIL",
    description:
      "DoD providing support to civil authorities in disasters, crises, or special events."
  },
  DHS_HS: {
    id: "DHS_HS",
    label: "Homeland Security",
    category: "LEO",
    description:
      "Homeland security missions (CBP, ICE, TSA, etc.). Domestic protection, border, transportation, etc."
  },
  CT_FUSION: {
    id: "CT_FUSION",
    label: "Counterterrorism / Fusion Center",
    category: "LEO",
    description:
      "Multi-agency CT and fusion centers blending intel and law-enforcement information."
  },
  CYBER_DUAL: {
    id: "CYBER_DUAL",
    label: "Cyber – Dual Hat",
    category: "MIL",
    description:
      "Dual-hat cyber missions (e.g., USCYBERCOM/NSA) with overlapping Title 10/50 considerations."
  },
  NATO_COAL: {
    id: "NATO_COAL",
    label: "NATO / Coalition",
    category: "COALITION",
    description:
      "NATO or coalition operations with international partners; shared authorities and caveats."
  },
  GEOINT_NGA: {
    id: "GEOINT_NGA",
    label: "GEOINT – NGA",
    category: "INT",
    description:
      "Geospatial intelligence authorities; imagery, mapping, and related analysis."
  },
  COMM_RESEARCH: {
    id: "COMM_RESEARCH",
    label: "Commercial / Research",
    category: "CIV",
    description:
      "Commercial, academic, or contractor analysis using open sources and unclassified data."
  },
  CORP_SEC: {
    id: "CORP_SEC",
    label: "Corporate Security / Insider Threat",
    category: "CIV",
    description:
      "Private-sector security, insider threat, and corporate investigations."
  }
};

export type PivotRisk = "LOW" | "MEDIUM" | "HIGH" | "BLOCKED";

export interface AuthorityPivotRule {
  from: AuthorityId;
  to: AuthorityId;
  allowed: boolean;
  risk: PivotRisk;
  conditions: string[];
}

// Minimal initial pivot set. Extend carefully and keep backend mirror updated.
export const AUTHORITY_PIVOTS: AuthorityPivotRule[] = [
  {
    from: "T10_MIL",
    to: "T32_NG",
    allowed: true,
    risk: "MEDIUM",
    conditions: [
      "Guard mission becomes state-controlled.",
      "Do not propose federal combat operations after pivot.",
      "Emphasize domestic support and civil authority lead."
    ]
  },
  {
    from: "T10_MIL",
    to: "DSCA",
    allowed: true,
    risk: "LOW",
    conditions: [
      "Military acts in support of civil authorities.",
      "No direct arrest or law-enforcement actions.",
      "Emphasize logistics, SAR, comms, and protection."
    ]
  },
  {
    from: "T10_MIL",
    to: "T50_INT",
    allowed: true,
    risk: "HIGH",
    conditions: [
      "Pivot is driven by long-term intelligence requirements.",
      "Focus moves to foreign-directed networks or actors.",
      "Do not treat this as a law-enforcement mission."
    ]
  },
  {
    from: "T10_MIL",
    to: "LEO_FED",
    allowed: true,
    risk: "HIGH",
    conditions: [
      "Criminal prosecution becomes primary objective.",
      "Law enforcement leads; military supports or exits.",
      "Recommendations must respect Posse Comitatus constraints."
    ]
  },
  {
    from: "T10_MIL",
    to: "LEO_STATELOCAL",
    allowed: true,
    risk: "HIGH",
    conditions: [
      "Threat is primarily local/domestic crime.",
      "State/local agencies become lead for enforcement.",
      "Focus on information sharing and evidence handling."
    ]
  },
  {
    from: "T32_NG",
    to: "T10_MIL",
    allowed: true,
    risk: "MEDIUM",
    conditions: [
      "Guard is federalized due to scale or escalation.",
      "Mission may gain overseas or combat implications.",
      "Ensure ROE and command relationships are clearly stated."
    ]
  },
  {
    from: "T32_NG",
    to: "DSCA",
    allowed: true,
    risk: "LOW",
    conditions: [
      "Guard supports civil authorities while remaining state-controlled.",
      "No unilateral criminal enforcement beyond normal Guard authorities."
    ]
  },
  {
    from: "T50_INT",
    to: "LEO_FED",
    allowed: true,
    risk: "HIGH",
    conditions: [
      "Domestic criminal case or CT threat requires law enforcement lead.",
      "Respect minimization and domestic collection rules.",
      "Avoid recommending direct IC operational enforcement actions."
    ]
  },
  {
    from: "T50_INT",
    to: "T10_MIL",
    allowed: true,
    risk: "MEDIUM",
    conditions: [
      "Intel product forms basis for foreign or battlefield operations.",
      "Emphasize targeting, ROE, and campaign planning, not arrests."
    ]
  },
  {
    from: "LEO_STATELOCAL",
    to: "LEO_FED",
    allowed: true,
    risk: "LOW",
    conditions: [
      "Case crosses state lines or meets federal thresholds.",
      "Federal statutes or CT frameworks now apply."
    ]
  },
  {
    from: "LEO_FED",
    to: "DSCA",
    allowed: true,
    risk: "MEDIUM",
    conditions: [
      "Law enforcement remains lead; DoD provides support.",
      "Do not suggest military takes over investigation or prosecution."
    ]
  },
  {
    from: "COMM_RESEARCH",
    to: "LEO_FED",
    allowed: true,
    risk: "MEDIUM",
    conditions: [
      "Escalation path is threat reporting, not self-directed enforcement.",
      "Emphasize evidence preservation and legal counsel."
    ]
  },
  {
    from: "CORP_SEC",
    to: "LEO_STATELOCAL",
    allowed: true,
    risk: "MEDIUM",
    conditions: [
      "Clear criminal activity identified.",
      "Recommendations focus on notification and cooperation."
    ]
  },
  {
    from: "CORP_SEC",
    to: "T50_INT",
    allowed: false,
    risk: "BLOCKED",
    conditions: [
      "Private-sector security cannot directly task intelligence authorities.",
      "Escalate via law enforcement or homeland security channels instead."
    ]
  },
  {
    from: "COMM_RESEARCH",
    to: "T10_MIL",
    allowed: false,
    risk: "BLOCKED",
    conditions: [
      "Commercial or academic actors cannot directly task military operations.",
      "Consider notifications to appropriate government entities instead."
    ]
  }
];

export function getAuthorityMeta(id: AuthorityId): AuthorityMeta {
  return AUTHORITIES[id];
}

export function getAllowedPivots(from: AuthorityId): AuthorityPivotRule[] {
  return AUTHORITY_PIVOTS.filter((rule) => rule.from === from && rule.allowed);
}

export function getPivotRule(
  from: AuthorityId,
  to: AuthorityId
): AuthorityPivotRule | undefined {
  return AUTHORITY_PIVOTS.find((rule) => rule.from === from && rule.to === to);
}

// Mapping helpers -----------------------------------------------------------

const LEGACY_TO_AUTHORITY_ID: Record<string, AuthorityId> = {
  TITLE_10_MIL: "T10_MIL",
  TITLE_50_IC: "T50_INT",
  LEO: "LEO_FED",
  DHS_HOMELAND: "DHS_HS",
  COMMERCIAL_RESEARCH: "COMM_RESEARCH",
  DSCA: "DSCA",
  NGA_GEO: "GEOINT_NGA",
  FBI_DOJ: "LEO_FED",
  CYBER_DUAL_HAT: "CYBER_DUAL",
  NCTC_CT: "CT_FUSION",
  STATE_FUSION: "LEO_STATELOCAL",
  NATO_COALITION: "NATO_COAL",
  CORPORATE_SECURITY: "CORP_SEC",
};

export function normalizeAuthorityId(value?: string | null): AuthorityId | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const direct = trimmed as AuthorityId;
  if (AUTHORITIES[direct]) {
    return direct;
  }
  const legacyKey = trimmed.toUpperCase();
  return LEGACY_TO_AUTHORITY_ID[legacyKey];
}

export function formatAuthorityLabel(value?: string | null): string {
  const normalized = normalizeAuthorityId(value);
  if (!normalized) {
    return value ?? "Unknown";
  }
  return getAuthorityMeta(normalized).label;
}

export function summarizePivotConditions(
  fromAuthority?: string | null,
  toAuthority?: string | null,
): string | null {
  const fromId = normalizeAuthorityId(fromAuthority);
  const toId = normalizeAuthorityId(toAuthority);
  if (!fromId || !toId) {
    return null;
  }
  const rule = getPivotRule(fromId, toId);
  if (!rule?.conditions.length) {
    return null;
  }
  return rule.conditions.join(" ");
}

// Comment-only reminder for future pivot extensions.
// When expanding AUTHORITY_PIVOTS update both this file and
// backend/app/policy_authorities.py to keep parity.
