const API_BASE_URL =
  process.env.NEXT_PUBLIC_APEX_API_BASE_URL ?? "http://localhost:8000";

type FetchOptions = RequestInit & { path: string };

async function request<T>({ path, ...options }: FetchOptions): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
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
}

export interface Document {
  id: number;
  mission_id: number;
  title?: string | null;
  content: string;
  include_in_analysis?: boolean;
  created_at: string;
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

export interface ModelInfo {
  name: string;
  source?: string;
}

export interface AvailableModelsResponse {
  models: ModelInfo[];
}

export interface ActiveModelResponse {
  active_model: string;
}

export async function fetchMissions(): Promise<Mission[]> {
  return request({ path: "/missions" });
}

export async function createMission(payload: {
  name: string;
  description?: string;
}): Promise<Mission> {
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

export async function fetchMissionDocuments(id: number): Promise<Document[]> {
  return request({ path: `/missions/${id}/documents` });
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

export async function fetchMissionGraph(missionId: number): Promise<{
  entities: Entity[];
  events: Event[];
}> {
  return request({ path: `/missions/${missionId}/graph` });
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
