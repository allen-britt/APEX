export interface AuthorityMetadata {
  code: string;
  label: string;
  description: string;
  prohibitions: string;
  allowedInts: string[];
}

export interface IntMetadataEntry {
  code: string;
  label: string;
  notes: string;
}

const AUTHORITY_METADATA: Record<string, AuthorityMetadata> = {
  TITLE_10_MIL: {
    code: "TITLE_10_MIL",
    label: "Title 10 – Military Operations",
    description:
      "Operational ISR and mission analysis for military forces with a foreign/battlefield focus.",
    prohibitions: "Do not propose domestic policing actions, arrests, or covert Title 50 tradecraft.",
    allowedInts: ["OSINT", "GEOINT", "SIGINT", "HUMINT", "MASINT", "ALL_SOURCE"],
  },
  TITLE_50_IC: {
    code: "TITLE_50_IC",
    label: "Title 50 – Intelligence",
    description: "Foreign intelligence and counterintelligence production for the IC.",
    prohibitions: "Avoid domestic arrests, kinetic strike tasking, or bulk U.S. person surveillance.",
    allowedInts: ["OSINT", "SIGINT", "HUMINT", "GEOINT", "MASINT", "CI_INT"],
  },
  LEO: {
    code: "LEO",
    label: "Law Enforcement",
    description: "Criminal case support, evidence development, and investigative analysis.",
    prohibitions: "Do not suggest warrantless searches, illegal surveillance, or military actions.",
    allowedInts: ["OSINT", "HUMINT", "GEOINT", "SIGINT", "LEO_CRIMINT"],
  },
  DHS_HOMELAND: {
    code: "DHS_HOMELAND",
    label: "DHS / Homeland Security",
    description: "Border, transportation, and infrastructure security missions.",
    prohibitions: "Stay within DHS authorities—no directing external military or LEO actions.",
    allowedInts: ["OSINT", "GEOINT", "HUMINT", "SIGINT", "CT_INT"],
  },
  COMMERCIAL_RESEARCH: {
    code: "COMMERCIAL_RESEARCH",
    label: "Commercial / Research",
    description: "Corporate security, academic research, and training scenarios.",
    prohibitions: "Never direct real-world arrests, kinetic options, or illegal hacking.",
    allowedInts: ["OSINT", "SOCMINT", "ALL_SOURCE"],
  },
  DSCA: {
    code: "DSCA",
    label: "Defense Support of Civil Authorities",
    description: "Military support to civil authorities during emergencies under civilian lead.",
    prohibitions: "Do not instruct soldiers to conduct arrests or policing activities.",
    allowedInts: ["OSINT", "GEOINT", "SIGINT", "ALL_SOURCE"],
  },
  NGA_GEO: {
    code: "NGA_GEO",
    label: "GEOINT – NGA",
    description: "Geospatial imagery, mapping, and terrain analysis to support decisions.",
    prohibitions: "Avoid persistent tracking of U.S. persons without a legal basis.",
    allowedInts: ["GEOINT", "OSINT", "SIGINT"],
  },
  FBI_DOJ: {
    code: "FBI_DOJ",
    label: "Federal Investigative – DOJ/FBI",
    description: "Federal criminal and national security investigations under DOJ authorities.",
    prohibitions: "Do not encourage surveillance or searches outside proper warrants/statutes.",
    allowedInts: ["OSINT", "HUMINT", "SIGINT", "GEOINT", "ALL_SOURCE"],
  },
  CYBER_DUAL_HAT: {
    code: "CYBER_DUAL_HAT",
    label: "Cyber – Dual Hat",
    description: "Joint NSA/CYBERCOM missions that separate intel and operational roles.",
    prohibitions: "No unauthorized offensive hacking or domestic data mixing.",
    allowedInts: ["SIGINT", "OSINT", "CYBINT"],
  },
  NCTC_CT: {
    code: "NCTC_CT",
    label: "Counterterrorism Fusion",
    description: "All-source CT fusion emphasizing civil liberties and interagency sharing.",
    prohibitions: "Do not design mass surveillance or treat communities as suspects without basis.",
    allowedInts: ["OSINT", "SIGINT", "HUMINT", "GEOINT", "CT_INT", "ALL_SOURCE"],
  },
  STATE_FUSION: {
    code: "STATE_FUSION",
    label: "State / Regional Fusion",
    description: "State-level intel and law-enforcement sharing centers.",
    prohibitions: "Avoid profiling based on protected classes or indiscriminate collection.",
    allowedInts: ["OSINT", "HUMINT", "GEOINT", "LEO_CRIMINT"],
  },
  NATO_COALITION: {
    code: "NATO_COALITION",
    label: "NATO / Coalition",
    description: "Multinational operations with releasability and caveat constraints.",
    prohibitions: "Do not mix NOFORN intel into releasable coalition products.",
    allowedInts: ["OSINT", "GEOINT", "SIGINT", "HUMINT", "ALL_SOURCE"],
  },
  CORPORATE_SECURITY: {
    code: "CORPORATE_SECURITY",
    label: "Corporate Security / Insider Threat",
    description: "Commercial physical/cyber security, insider threat, and fraud prevention.",
    prohibitions: "Never recommend unlawful monitoring, wiretaps, or privacy violations.",
    allowedInts: ["OSINT", "SOCMINT", "ALL_SOURCE"],
  },
};

const INT_METADATA: Record<string, IntMetadataEntry> = {
  OSINT: {
    code: "OSINT",
    label: "OSINT – Open-Source",
    notes: "Public/commercial data governed by privacy, ToS, and civil liberties constraints.",
  },
  HUMINT: {
    code: "HUMINT",
    label: "HUMINT – Human Intelligence",
    notes: "Source handling, consent, and tradecraft rules apply; no automated tasking of people.",
  },
  SIGINT: {
    code: "SIGINT",
    label: "SIGINT – Signals",
    notes: "Highly regulated intercept data; watch for U.S. person minimization requirements.",
  },
  GEOINT: {
    code: "GEOINT",
    label: "GEOINT – Geospatial",
    notes: "Imagery/geospatial data; avoid privacy violations or targeting domestic individuals.",
  },
  MASINT: {
    code: "MASINT",
    label: "MASINT – Measurement & Signature",
    notes: "Specialized sensing with unique classification and handling caveats.",
  },
  CYBINT: {
    code: "CYBINT",
    label: "CYBINT – Cyber Intelligence",
    notes: "Technical telemetry about cyber operations; ensure legal authorities for collection.",
  },
  FININT: {
    code: "FININT",
    label: "FININT – Financial",
    notes: "Financial reporting with strict privacy and compliance requirements.",
  },
  TECHINT: {
    code: "TECHINT",
    label: "TECHINT – Technical Intelligence",
    notes: "Material exploitation data; follow export controls and handling limits.",
  },
  SOCMINT: {
    code: "SOCMINT",
    label: "SOCMINT – Social Media",
    notes: "Social platform collection, emphasizing ToS compliance and minimization.",
  },
  ALL_SOURCE: {
    code: "ALL_SOURCE",
    label: "All-Source",
    notes: "Fusion of multiple INTs—must honor the most restrictive source constraints.",
  },
  LEO_CRIMINT: {
    code: "LEO_CRIMINT",
    label: "LEO CRIMINT",
    notes: "Criminal intelligence for law enforcement with evidentiary integrity rules.",
  },
  CT_INT: {
    code: "CT_INT",
    label: "CT INT",
    notes: "Counterterrorism reporting shared across partners; guard against over-collection.",
  },
  CI_INT: {
    code: "CI_INT",
    label: "CI INT",
    notes: "Counterintelligence material with strict classification and need-to-know limits.",
  },
  CASE_INT: {
    code: "CASE_INT",
    label: "CASEINT – Investigative Case Intel",
    notes: "Law-enforcement case evidence, subject packets, and investigative leads.",
  },
};

const AUTHORITY_LIST = Object.values(AUTHORITY_METADATA);
const INT_LIST = Object.values(INT_METADATA);

export function describeAuthority(code?: string | null): AuthorityMetadata | undefined {
  if (!code) {
    return undefined;
  }
  return AUTHORITY_METADATA[code.toUpperCase()];
}

export function describeInt(code?: string | null): IntMetadataEntry | undefined {
  if (!code) {
    return undefined;
  }
  return INT_METADATA[code.toUpperCase()];
}

export function formatIntLabel(code?: string | null): string {
  const meta = describeInt(code);
  return meta ? meta.label : code ?? "Unknown INT";
}

export function getAuthorityLabel(code?: string | null): string {
  const meta = describeAuthority(code);
  return meta ? meta.label : code ?? "Unknown authority";
}

export function listAuthorities(): AuthorityMetadata[] {
  return AUTHORITY_LIST;
}

export function listIntOptions(): IntMetadataEntry[] {
  return INT_LIST;
}

export function validateAuthorityIntSelection(
  authorityCode: string | null | undefined,
  intCodes: string[],
): string[] {
  if (!authorityCode || !intCodes.length) {
    return [];
  }
  const meta = describeAuthority(authorityCode);
  if (!meta?.allowedInts.length) {
    return [];
  }
  const normalized = Array.from(
    new Set(
      intCodes
        .map((code) => code?.trim().toUpperCase())
        .filter((code): code is string => Boolean(code)),
    ),
  );
  const disallowed = normalized.filter((code) => !meta.allowedInts.includes(code));
  if (!disallowed.length) {
    return [];
  }
  return disallowed.map(
    (code) => `${formatIntLabel(code)} is not authorized under the ${meta.label} lane.`,
  );
}
