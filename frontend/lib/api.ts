const INTERNAL_API_BASE_URL = process.env.APEX_INTERNAL_API_BASE_URL;
const PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_APEX_API_BASE_URL;

function resolveApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return (
      INTERNAL_API_BASE_URL ??
      PUBLIC_API_BASE_URL ??
      "http://localhost:8000"
    );
  }

  if (PUBLIC_API_BASE_URL) {
    return PUBLIC_API_BASE_URL;
  }

  const { protocol, hostname } = window.location;
  const port = "8000";
  return `${protocol}//${hostname}:${port}`;
}

type FetchOptions = RequestInit & { path: string };

async function request<T>({ path, ...options }: FetchOptions): Promise<T> {
  const url = `${resolveApiBaseUrl()}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}

export interface Mission {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  primary_authority?: string;
  original_authority?: string;
  secondary_authorities?: string[];
  int_types?: string[];
  kg_namespace?: string | null;
  gap_analysis?: Record<string, unknown> | null;
  template_reports?: TemplateReportRecord[];
  authority_pivots?: MissionAuthorityPivot[];
  latest_agent_run?: AgentRun | null;
}

export interface MissionCreatePayload {
  name: string;
  description?: string;
  primary_authority: string;
  secondary_authorities?: string[];
  int_types: string[];
}

export interface MissionAuthorityPivot {
  id: number;
  from_authority: string;
  to_authority: string;
  justification: string;
  risk: string;
  conditions: string[];
  actor?: string | null;
  created_at: string;
}

export interface MissionAuthorityPivotRequest {
  target_authority: string;
  justification: string;
}

export interface Document {
  id: number;
  mission_id: number;
  title?: string | null;
  content: string;
  include_in_analysis?: boolean;
  created_at: string;
}

export interface HumintIirParsedFields {
  report_number?: string | null;
  source_id?: string | null;
  collection_unit?: string | null;
  collection_date?: string | null;
  report_date?: string | null;
  region?: string | null;
  target_persons?: string[];
  target_locations?: string[];
  summary?: string | null;
  handling_instructions?: string | null;
  [key: string]: string | string[] | null | undefined;
}

export interface HumintInsight {
  id?: number | null;
  title: string;
  detail: string;
  confidence: number;
  supporting_evidence_ids: number[];
}

export interface HumintGap {
  title: string;
  description: string;
  priority: number;
  suggested_collection?: string | null;
}

export interface HumintFollowup {
  question: string;
  rationale: string;
  priority: number;
  related_gap_titles: string[];
  suggested_channel?: string | null;
}

export interface HumintIirAnalysisResult {
  mission_id: number;
  document_id: number;
  parsed_fields: HumintIirParsedFields;
  key_insights: HumintInsight[];
  contradictions: string[];
  gaps: HumintGap[];
  followups: HumintFollowup[];
  evidence_document_ids: number[];
  model_name?: string | null;
  run_id?: number | null;
}

export interface MissionSourceDocument {
  id: string;
  mission_id: number;
  source_type: string;
  title?: string | null;
  original_path?: string | null;
  primary_int?: string | null;
  int_types: string[];
  aggregator_doc_id?: string | null;
  status: string;
  created_at: string;
  ingest_status?: string | null;
  ingest_error?: string | null;
  kg_nodes_before?: number | null;
  kg_nodes_after?: number | null;
  kg_edges_before?: number | null;
  kg_edges_after?: number | null;
  kg_nodes_delta?: number | null;
  kg_edges_delta?: number | null;
}

export interface AgentRun {
  id: number;
  mission_id: number;
  status: string;
  summary?: string | null;
  next_steps?: string | null;
  guardrail_status: string;
  guardrail_issues?: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface Entity {
  id: number;
  mission_id: number;
  name: string;
  type?: string | null;
  description?: string | null;
  created_at: string;
}

export interface Event {
  id: number;
  mission_id: number;
  title: string;
  summary?: string | null;
  timestamp?: string | null;
  location?: string | null;
  involved_entity_ids?: number[] | null;
  created_at: string;
}

export interface MissionDataset {
  id: number;
  mission_id: number;
  name: string;
  status: string;
  sources: unknown;
  profile?: unknown;
  semantic_profile?: unknown;
  created_at: string;
  updated_at?: string;
}

export interface ModelInfo {
  name: string;
  source?: string;
}

export interface GuardrailReport {
  overall_score: string;
  issues: string[];
}

export interface MissionReport {
  mission: Mission;
  documents: Document[];
  run: AgentRun | null;
  entities: Entity[];
  events: Event[];
  guardrail?: GuardrailReport | null;
  gaps?: string[] | null;
  next_steps?: string[] | null;
  delta_summary?: string | null;
  generated_at: string;
}

export interface AvailableModelsResponse {
  models: ModelInfo[];
}

export interface ActiveModelResponse {
  active_model: string;
}

export interface GapFinding {
  title: string;
  detail?: string | null;
  severity?: string;
  metadata?: Record<string, unknown> | null;
}

export interface PriorityEntry {
  name: string;
  reason: string;
  type?: string | null;
  score?: number | null;
  reference_id?: number | null;
}

export interface PrioritiesBlock {
  entities: PriorityEntry[];
  events: PriorityEntry[];
  rationale: string;
}

export interface GapAnalysisResponse {
  generated_at: string;
  kg_summary?: Record<string, unknown> | null;
  missing_data: GapFinding[];
  time_gaps: GapFinding[];
  conflicts: GapFinding[];
  high_value_unknowns: GapFinding[];
  quality_findings: GapFinding[];
  priorities: PrioritiesBlock;
}

export interface ReportTemplateSummary {
  id: string;
  name: string;
  description?: string;
  int_type?: string | null;
  mission_domains: string[];
  title10_allowed: boolean;
  title50_allowed: boolean;
  sections?: string[];
}

export interface ReportTemplateSection {
  id: string;
  title: string;
  content: string;
}

export type ReportTemplateId =
  | "leo_case_summary_v1"
  | "osint_pattern_of_life_leo_v1"
  | "full_intrep_v1"
  | "delta_update_v1"
  | "commander_decision_sheet_v1"
  | string;

export interface ReportTemplateResponse {
  template_id: ReportTemplateId;
  template_name: string;
  sections: ReportTemplateSection[];
  metadata: TemplateReportMetadata;
}

export interface TemplateReportRecord {
  id: string;
  template_id: ReportTemplateId;
  template_name: string;
  sections: ReportTemplateSection[];
  metadata: TemplateReportMetadata;
  stored_at: string;
}

export interface TemplateReportResponse {
  mission_id: number;
  template_id: ReportTemplateId;
  template_name: string;
  html: string;
  markdown: string;
  sections?: ReportTemplateSection[] | null;
  metadata?: TemplateReportMetadata;
}

export interface CourseOfAction {
  id: string;
  decision_id: string;
  label: string;
  summary: string;
  pros: string[];
  cons: string[];
  risk_level: "low" | "medium" | "high" | "critical";
  policy_alignment: "compliant" | "waiver_required" | "conflicts";
  policy_refs: string[];
  confidence: number | null;
}

export interface PolicyCheck {
  id: string;
  rule_name: string;
  outcome: "pass" | "fail" | "waiver";
  summary: string;
  source_ref: string;
}

export interface DecisionPrecedent {
  id: string;
  mission_id: string;
  mission_name: string;
  run_id?: string;
  summary: string;
  outcome_summary?: string;
}

export interface DecisionBlindSpot {
  id: string;
  description: string;
  impact: "low" | "medium" | "high";
  mitigation?: string;
}

export interface MissionDecision {
  id: string;
  question: string;
  status: "pending" | "decided" | "deferred";
  recommended_coa_id?: string;
  selected_coa_id?: string;
  rationale?: string;
}

export interface DecisionDataset {
  decisions: MissionDecision[];
  courses_of_action: CourseOfAction[];
  policy_checks: PolicyCheck[];
  precedents: DecisionPrecedent[];
  blind_spots: DecisionBlindSpot[];
  system_confidence?: number;
}

export interface TemplateReportMetadata {
  generated_at?: string;
  kg_snapshot_summary?: string;
  latest_agent_run?: AgentRun | null;
  guardrail_status?: string | null;
  guardrail_issues?: string[];
  guardrail?: {
    state: "ok" | "warning" | "blocked" | "caution" | string;
    summary?: string;
  };
  decisions?: DecisionDataset;
  [key: string]: unknown;
}

export interface GapItem {
  id: string;
  description: string;
  severity: string;
  int_types_impacted: string[];
  evidence_notes?: string | null;
}

export interface RecommendedAction {
  id: string;
  description: string;
  authority_scope: string;
  allowed_under_mission_authority: boolean;
  rationale?: string | null;
  related_gap_ids: string[];
}

export interface GapAnalysisResult {
  mission_id: number;
  mission_authority: string;
  coverage_summary: Record<string, unknown>;
  gaps: GapItem[];
  recommended_actions: RecommendedAction[];
  overall_assessment?: string | null;
}

export interface ReportTemplate {
  template_id: ReportTemplateId;
  name: string;
  description?: string | null;
  int_type: string;
  mission_domains: string[];
  title10_allowed: boolean;
  title50_allowed: boolean;
  sections?: string[] | null;
}

export type ComponentStatusValue = string | { status?: string; detail?: string; model?: string };

export interface SystemStatus {
  overall: string;
  backend: ComponentStatusValue;
  aggregator: ComponentStatusValue;
  llm: ComponentStatusValue;
}

export interface KgLabelCount {
  label: string;
  count: number;
}

export interface MissionKgSummary {
  nodes: number;
  edges: number;
  top_labels: KgLabelCount[];
}

export interface KgGraphPayload {
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
}

export type KgNeighborhoodPayload = KgGraphPayload;

export interface KgLinkSuggestion {
  src?: string | number;
  dst?: string | number;
  reason?: string;
  confidence?: number;
  [key: string]: unknown;
}

export async function fetchMissions(): Promise<Mission[]> {
  return request({ path: "/missions" });
}

export async function createMission(payload: MissionCreatePayload): Promise<Mission> {
  return request({
    path: "/missions",
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchMission(id: number): Promise<Mission> {
  return request({ path: `/missions/${id}` });
}

export async function deleteMission(id: number): Promise<void> {
  await request({ path: `/missions/${id}`, method: "DELETE" });
}

export async function pivotMissionAuthority(
  id: number,
  payload: MissionAuthorityPivotRequest,
): Promise<Mission> {
  return request({
    path: `/missions/${id}/pivot-authority`,
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchMissionDocuments(id: number): Promise<Document[]> {
  return request({ path: `/missions/${id}/documents` });
}

export async function fetchMissionSourceDocuments(id: number): Promise<MissionSourceDocument[]> {
  return request({ path: `/missions/${id}/mission-documents` });
}

export async function analyzeHumintIir(
  missionId: number,
  documentId: number,
): Promise<HumintIirAnalysisResult> {
  return request({
    path: `/missions/${missionId}/humint/documents/${documentId}/analyze`,
    method: "POST",
  });
}

export async function createDocument(
  missionId: number,
  payload: { title?: string; content: string },
): Promise<Document> {
  return request({
    path: `/missions/${missionId}/documents`,
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteDocument(id: number): Promise<void> {
  await request({ path: `/documents/${id}`, method: "DELETE" });
}

export async function deleteMissionSourceDocument(missionId: number, documentId: string): Promise<void> {
  await request({ path: `/missions/${missionId}/mission-documents/${documentId}`, method: "DELETE" });
}

export async function moveDocumentToMission(
  documentId: number,
  missionId: number,
): Promise<Document> {
  return request({
    path: `/documents/${documentId}`,
    method: "PATCH",
    body: JSON.stringify({ mission_id: missionId }),
  });
}

export async function setDocumentIncludeInAnalysis(
  documentId: number,
  include: boolean,
): Promise<Document> {
  return request({
    path: `/documents/${documentId}`,
    method: "PATCH",
    body: JSON.stringify({ include_in_analysis: include }),
  });
}

interface MissionDocumentUploadPayload {
  file: File;
  title?: string;
  primary_int?: string;
  int_types?: string[];
}

export async function uploadMissionSourceFile(
  missionId: number,
  payload: MissionDocumentUploadPayload,
): Promise<MissionSourceDocument> {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.title) {
    form.append("title", payload.title);
  }
  if (payload.primary_int) {
    form.append("primary_int", payload.primary_int);
  }
  (payload.int_types ?? []).forEach((code) => {
    form.append("int_types", code);
  });

  const response = await fetch(`${resolveApiBaseUrl()}/missions/${missionId}/documents/upload`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to upload mission document");
  }

  return (await response.json()) as MissionSourceDocument;
}

interface MissionDocumentUrlPayload {
  url: string;
  title?: string;
  primary_int?: string;
  int_types?: string[];
}

export async function ingestMissionDocumentUrl(
  missionId: number,
  payload: MissionDocumentUrlPayload,
): Promise<MissionSourceDocument> {
  return request({
    path: `/missions/${missionId}/documents/url`,
    method: "POST",
    body: JSON.stringify({
      url: payload.url,
      title: payload.title,
      primary_int: payload.primary_int,
      int_types: payload.int_types ?? [],
    }),
  });
}

export async function fetchAgentRuns(missionId: number): Promise<AgentRun[]> {
  return request({ path: `/missions/${missionId}/agent_runs` });
}

export async function analyzeMission(missionId: number): Promise<AgentRun> {
  return request({
    path: `/missions/${missionId}/analyze`,
    method: "POST",
  });
}

export async function deleteAgentRun(runId: number): Promise<void> {
  await request({ path: `/agent_runs/${runId}`, method: "DELETE" });
}

export async function clearMissionAgentRuns(missionId: number): Promise<void> {
  await request({ path: `/missions/${missionId}/agent_runs`, method: "DELETE" });
}

export async function deleteEntity(entityId: number): Promise<void> {
  await request({ path: `/entities/${entityId}`, method: "DELETE" });
}

export async function clearMissionEntities(missionId: number): Promise<void> {
  await request({ path: `/missions/${missionId}/entities`, method: "DELETE" });
}

export async function deleteEvent(eventId: number): Promise<void> {
  await request({ path: `/events/${eventId}`, method: "DELETE" });
}

export async function clearMissionEvents(missionId: number): Promise<void> {
  await request({ path: `/missions/${missionId}/events`, method: "DELETE" });
}

export async function getMissionReport(missionId: number, runId?: number): Promise<MissionReport> {
  const search = new URLSearchParams();
  if (runId) {
    search.set("run_id", String(runId));
  }
  const query = search.toString();
  const path = query
    ? `/missions/${missionId}/report?${search.toString()}`
    : `/missions/${missionId}/report`;
  return request({ path });
}

export async function fetchMissionGraph(missionId: number): Promise<{
  entities: Entity[];
  events: Event[];
}> {
  return request({ path: `/missions/${missionId}/graph` });
}

export async function fetchMissionKgSummary(missionId: number): Promise<MissionKgSummary> {
  return request({ path: `/missions/${missionId}/kg/summary` });
}

export async function fetchMissionKgGraph(
  missionId: number,
  options?: { limitNodes?: number; limitEdges?: number },
): Promise<KgGraphPayload> {
  const params = new URLSearchParams();
  if (typeof options?.limitNodes === "number") {
    params.set("limit_nodes", String(options.limitNodes));
  }
  if (typeof options?.limitEdges === "number") {
    params.set("limit_edges", String(options.limitEdges));
  }
  const query = params.toString();
  const path = query ? `/missions/${missionId}/kg/full?${query}` : `/missions/${missionId}/kg/full`;
  return request({ path });
}

export async function fetchMissionKgNeighborhood(
  missionId: number,
  nodeId: string,
  options?: { hops?: number },
): Promise<KgNeighborhoodPayload> {
  const params = new URLSearchParams({ node_id: nodeId });
  if (typeof options?.hops === "number") {
    params.set("hops", String(options.hops));
  }
  return request({ path: `/missions/${missionId}/kg/neighborhood?${params.toString()}` });
}

export async function fetchMissionKgLinkSuggestions(
  missionId: number,
  options?: { limit?: number },
): Promise<{ suggestions?: KgLinkSuggestion[]; [key: string]: unknown }>
{
  const params = new URLSearchParams();
  if (typeof options?.limit === "number") {
    params.set("limit", String(options.limit));
  }
  const query = params.toString();
  const path = query
    ? `/missions/${missionId}/kg/suggest-links?${query}`
    : `/missions/${missionId}/kg/suggest-links`;
  return request({ path });
}

export async function fetchMissionDatasets(missionId: number): Promise<MissionDataset[]> {
  return request({ path: `/missions/${missionId}/datasets` });
}

export async function createMissionDataset(
  missionId: number,
  payload: { name: string; sources: unknown[] },
): Promise<MissionDataset> {
  return request({
    path: `/missions/${missionId}/datasets`,
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function buildMissionDatasetSemanticProfile(
  missionId: number,
  datasetId: number,
): Promise<MissionDataset> {
  return request({
    path: `/missions/${missionId}/datasets/${datasetId}/semantic_profile`,
    method: "POST",
  });
}

export async function fetchGapAnalysis(
  missionId: number,
  options?: { forceRegenerate?: boolean },
): Promise<GapAnalysisResponse> {
  const search = new URLSearchParams();
  if (options?.forceRegenerate) {
    search.set("force_regen", "true");
  }
  const query = search.toString();
  const path = query
    ? `/missions/${missionId}/analysis/gaps?${query}`
    : `/missions/${missionId}/analysis/gaps`;
  return request({ path });
}

export async function fetchReportTemplates(): Promise<ReportTemplateSummary[]> {
  return request({ path: "/reports/templates" });
}

export async function runGapAnalysis(missionId: number): Promise<GapAnalysisResponse> {
  return fetchGapAnalysis(missionId, { forceRegenerate: true });
}

export async function fetchMissionReportTemplates(
  missionId: number,
): Promise<ReportTemplate[]> {
  const search = new URLSearchParams({ mission_id: String(missionId) });
  const data = await request<ReportTemplateSummary[]>({ path: `/reports/templates?${search.toString()}` });
  return data.map((tpl) => ({
    template_id: tpl.id,
    name: tpl.name,
    description: tpl.description,
    int_type: tpl.int_type ?? "ALL_SOURCE",
    mission_domains: tpl.mission_domains,
    title10_allowed: tpl.title10_allowed,
    title50_allowed: tpl.title50_allowed,
    sections: tpl.sections ?? [],
  }));
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  return request({ path: "/status" });
}

export async function fetchTemplateReportHistory(
  missionId: number,
): Promise<TemplateReportRecord[]> {
  return request({ path: `/missions/${missionId}/reports/templates` });
}

export async function generateMissionTemplateReport(
  missionId: number,
  payload: { template_id: string },
): Promise<TemplateReportResponse> {
  return request({
    path: `/missions/${missionId}/reports/from_template`,
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generateTemplateReport(
  missionId: number,
  templateId: string,
  options?: { persist?: boolean },
): Promise<TemplateReportResponse> {
  // Legacy helper: funnel to new endpoint, persisting handled server-side when enabled
  return generateMissionTemplateReport(missionId, { template_id: templateId });
}

export async function fetchAvailableModels(): Promise<AvailableModelsResponse> {
  return request({ path: "/models/available" });
}

export async function fetchActiveModelInfo(): Promise<ActiveModelResponse> {
  return request({ path: "/settings/model" });
}

export async function setActiveModel(model: string): Promise<ActiveModelResponse> {
  return request({
    path: "/settings/model",
    method: "POST",
    body: JSON.stringify({ model }),
  });
}

export { request };
