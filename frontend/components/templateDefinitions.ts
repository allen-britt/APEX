import type { ReportTemplateId } from "@/lib/api";

export interface TemplateDefinition {
  id: ReportTemplateId;
  label: string;
  description: string;
}

export const TEMPLATE_DEFINITIONS: readonly TemplateDefinition[] = [
  {
    id: "leo_case_summary_v1",
    label: "LEO Case Summary",
    description: "Structured case narrative for investigators and prosecutors.",
  },
  {
    id: "osint_pattern_of_life_leo_v1",
    label: "OSINT Pattern of Life (LEO)",
    description: "Subject’s online footprint, behavior, and risk.",
  },
  {
    id: "full_intrep_v1",
    label: "Full Intelligence Report",
    description: "Comprehensive intelligence estimate for leadership.",
  },
  {
    id: "delta_update_v1",
    label: "Delta Update",
    description: "Highlights what changed since the previous report/run.",
  },
  {
    id: "commander_decision_sheet_v1",
    label: "Commander Decision Sheet",
    description: "Courses of action, risks, policy checks, and blind spots.",
  },
] as const;

export const TEMPLATE_DEFINITION_MAP = TEMPLATE_DEFINITIONS.reduce<Record<string, TemplateDefinition>>((acc, def) => {
  acc[def.id] = def;
  return acc;
}, {});
