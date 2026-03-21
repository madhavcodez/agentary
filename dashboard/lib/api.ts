import type {
  ExpertAgent,
  Finding,
  HealthCheck,
  Mission,
  MissionLiveStatus,
  MissionFinding,
  AlertItem,
  MonitorSummary,
  Project,
  WorkflowData,
  WorkflowTemplate,
  Report,
  ReportFull,
  ShareResponse,
  VoiceExtraction,
  Workflow,
} from "./types";
import { type AuthUser, getToken, logout, setToken, setUser } from "./auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (res.status === 401) {
    logout();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// ── Auth ───────────────────────────────────────────────────────────

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export async function loginApi(email: string, password: string): Promise<TokenResponse> {
  const url = `${BASE_URL}/auth/login`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(body.detail || "Invalid credentials");
  }

  const data = (await res.json()) as TokenResponse;
  setToken(data.access_token);
  setUser(data.user);
  return data;
}

export async function registerApi(
  email: string,
  password: string,
  name: string,
): Promise<TokenResponse> {
  const url = `${BASE_URL}/auth/register`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Registration failed" }));
    throw new Error(body.detail || "Registration failed");
  }

  const data = (await res.json()) as TokenResponse;
  setToken(data.access_token);
  setUser(data.user);
  return data;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me");
}

// ── Health ──────────────────────────────────────────────────────────

export function fetchHealth(): Promise<HealthCheck> {
  return request<HealthCheck>("/health");
}

// ── Projects ────────────────────────────────────────────────────────

export function fetchProjects(): Promise<Project[]> {
  return request<Project[]>("/api/projects");
}

export function createProject(data: {
  name: string;
  description?: string;
  project_type?: string;
  domain_context?: string;
}): Promise<Project> {
  return request<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchProject(id: string): Promise<Project> {
  return request<Project>(`/api/projects/${id}`);
}

export function updateProject(
  id: string,
  data: {
    name?: string;
    description?: string;
    project_type?: string;
    domain_context?: string;
  },
): Promise<Project> {
  return request<Project>(`/api/projects/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ── Missions ────────────────────────────────────────────────────────

export function fetchMissions(params?: {
  project_id?: string;
  status?: string;
  page?: number;
  limit?: number;
}): Promise<Mission[]> {
  const sp = new URLSearchParams();
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.status) sp.set("status", params.status);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<Mission[]>(`/api/missions${qs ? `?${qs}` : ""}`);
}

export function createMission(data: {
  project_id: string;
  name: string;
  description?: string;
  objective?: string;
  mission_type?: string;
}): Promise<Mission> {
  return request<Mission>("/api/missions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function triggerMissionRun(missionId: string): Promise<Mission> {
  return request<Mission>(`/api/missions/${missionId}/run`, {
    method: "POST",
  });
}

export function startMission(id: string): Promise<Mission> {
  return request<Mission>(`/api/missions/${id}/start`, { method: "POST" });
}

export function stopMission(id: string): Promise<Mission> {
  return request<Mission>(`/api/missions/${id}/stop`, { method: "POST" });
}

export function rerunMission(id: string): Promise<Mission> {
  return request<Mission>(`/api/missions/${id}/rerun`, { method: "POST" });
}

export function fetchMissionStatus(id: string): Promise<MissionLiveStatus> {
  return request<MissionLiveStatus>(`/api/missions/${id}/status`);
}

export function fetchMissionFindings(
  id: string,
  params?: { page?: number; limit?: number },
): Promise<{ items: MissionFinding[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<{ items: MissionFinding[]; total: number }>(
    `/api/missions/${id}/findings${qs ? `?${qs}` : ""}`,
  );
}

// ── Expert Agents ───────────────────────────────────────────────────

export function fetchExpertAgents(): Promise<ExpertAgent[]> {
  return request<ExpertAgent[]>("/api/expert-agents");
}

// ── Findings ────────────────────────────────────────────────────────

export function fetchFindings(params?: {
  project_id?: string;
  mission_id?: string;
  finding_type?: string;
  page?: number;
  limit?: number;
}): Promise<Finding[]> {
  const sp = new URLSearchParams();
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.mission_id) sp.set("mission_id", params.mission_id);
  if (params?.finding_type) sp.set("finding_type", params.finding_type);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<Finding[]>(`/api/findings${qs ? `?${qs}` : ""}`);
}

// ── Reports ─────────────────────────────────────────────────────────

export function fetchReports(params?: {
  project_id?: string;
  report_type?: string;
  page?: number;
  limit?: number;
}): Promise<Report[]> {
  const sp = new URLSearchParams();
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.report_type) sp.set("report_type", params.report_type);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<Report[]>(`/api/reports${qs ? `?${qs}` : ""}`);
}

// ── Voice Extractions ───────────────────────────────────────────────

export function fetchVoiceExtractions(params?: {
  project_id?: string;
  status?: string;
  page?: number;
  limit?: number;
}): Promise<VoiceExtraction[]> {
  const sp = new URLSearchParams();
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.status) sp.set("status", params.status);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<VoiceExtraction[]>(`/api/voice-extractions${qs ? `?${qs}` : ""}`);
}

// ── Workflows ───────────────────────────────────────────────────────

export function fetchWorkflows(params?: {
  category?: string;
  page?: number;
  limit?: number;
}): Promise<Workflow[]> {
  const sp = new URLSearchParams();
  if (params?.category) sp.set("category", params.category);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<Workflow[]>(`/api/workflows${qs ? `?${qs}` : ""}`);
}

export function createWorkflow(data: {
  name: string;
  description?: string;
  category?: string;
  nodes?: unknown[];
  edges?: unknown[];
  variables?: Record<string, unknown>;
  trigger_type?: string;
  trigger_config?: Record<string, unknown>;
  created_from?: string;
  project_id?: string;
}): Promise<WorkflowData> {
  return request<WorkflowData>("/api/workflows", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchWorkflow(id: string): Promise<WorkflowData> {
  return request<WorkflowData>(`/api/workflows/${id}`);
}

export function updateWorkflow(
  id: string,
  data: Record<string, unknown>,
): Promise<WorkflowData> {
  return request<WorkflowData>(`/api/workflows/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteWorkflow(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/workflows/${id}`, { method: "DELETE" });
}

export function activateWorkflow(id: string): Promise<WorkflowData> {
  return request<WorkflowData>(`/api/workflows/${id}/activate`, { method: "POST" });
}

export function pauseWorkflow(id: string): Promise<WorkflowData> {
  return request<WorkflowData>(`/api/workflows/${id}/pause`, { method: "POST" });
}

export function triggerWorkflowRun(id: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/workflows/${id}/run`, { method: "POST" });
}

export function fetchWorkflowRuns(
  workflowId: string,
  params?: { page?: number; limit?: number },
): Promise<Record<string, unknown>[]> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<Record<string, unknown>[]>(`/api/workflows/${workflowId}/runs${qs ? `?${qs}` : ""}`);
}

export function validateWorkflowApi(id: string): Promise<{ valid: boolean; errors: string[] }> {
  return request<{ valid: boolean; errors: string[] }>(`/api/workflows/${id}/validate`, { method: "POST" });
}

export function createWorkflowFromTemplate(data: {
  template_id: string;
  variables: Record<string, unknown>;
  project_id?: string;
  name?: string;
}): Promise<WorkflowData> {
  return request<WorkflowData>("/api/workflows/from-template", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function createWorkflowFromDescription(data: {
  description: string;
  project_id?: string;
}): Promise<WorkflowData> {
  return request<WorkflowData>("/api/workflows/from-description", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchWorkflowTemplates(category?: string): Promise<WorkflowTemplate[]> {
  const qs = category ? `?category=${category}` : "";
  return request<WorkflowTemplate[]>(`/api/workflow-templates${qs}`);
}

import type { WorkflowRun } from "./types";

export function fetchWorkflowRun(workflowId: string, runId: string): Promise<WorkflowRun> {
  return request<WorkflowRun>(`/api/workflows/${workflowId}/runs/${runId}`);
}

// ── Reports extended ──────────────────────────────────────────────────

export function fetchReport(id: string): Promise<ReportFull> {
  return request<ReportFull>(`/reports/${id}`);
}

export function updateReport(
  id: string,
  data: { title?: string; description?: string },
): Promise<ReportFull> {
  return request<ReportFull>(`/reports/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteReport(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/reports/${id}`, { method: "DELETE" });
}

export function regenerateReport(id: string): Promise<ReportFull> {
  return request<ReportFull>(`/reports/${id}/regenerate`, { method: "POST" });
}

export function regenerateSection(
  reportId: string,
  sectionIndex: number,
  instructions?: string,
): Promise<ReportFull> {
  return request<ReportFull>(`/reports/${reportId}/regenerate-section`, {
    method: "POST",
    body: JSON.stringify({ section_index: sectionIndex, instructions }),
  });
}

export function downloadReportPdf(id: string): string {
  const token = getToken();
  return `${BASE_URL}/reports/${id}/pdf${token ? `?token=${token}` : ""}`;
}

export function createShareLink(reportId: string): Promise<ShareResponse> {
  return request<ShareResponse>(`/reports/${reportId}/share`, { method: "POST" });
}

export function revokeShareLink(reportId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/reports/${reportId}/share`, { method: "DELETE" });
}

export function fetchSharedReport(token: string): Promise<ReportFull> {
  const url = `${BASE_URL}/shared/reports/${token}`;
  return fetch(url, { cache: "no-store" }).then((res) => {
    if (!res.ok) throw new Error("Report not found");
    return res.json() as Promise<ReportFull>;
  });
}

export function exportFindingsCsvUrl(missionId: string): string {
  return `${BASE_URL}/export/missions/${missionId}/findings/csv`;
}

export function exportFindingsExcelUrl(missionId: string): string {
  return `${BASE_URL}/export/missions/${missionId}/findings/excel`;
}

export function exportFindingsJsonUrl(missionId: string): string {
  return `${BASE_URL}/export/missions/${missionId}/findings/json`;
}

// ── Monitors ────────────────────────────────────────────────────────

export function fetchMonitors(params?: {
  project_id?: string;
  status?: string;
  page?: number;
  limit?: number;
}): Promise<MonitorSummary[]> {
  const sp = new URLSearchParams();
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.status) sp.set("status", params.status);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<MonitorSummary[]>(`/api/monitors${qs ? `?${qs}` : ""}`);
}

export function createMonitor(data: {
  project_id?: string;
  name: string;
  monitor_type: string;
  check_config?: Record<string, unknown>;
  alert_config?: Record<string, unknown>;
  schedule_cron?: string;
  timezone?: string;
  description?: string;
}): Promise<MonitorSummary> {
  return request<MonitorSummary>("/api/monitors", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deleteMonitor(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/monitors/${id}`, { method: "DELETE" });
}

export function pauseMonitor(id: string): Promise<MonitorSummary> {
  return request<MonitorSummary>(`/api/monitors/${id}/pause`, { method: "POST" });
}

export function resumeMonitor(id: string): Promise<MonitorSummary> {
  return request<MonitorSummary>(`/api/monitors/${id}/resume`, { method: "POST" });
}

export function triggerMonitorCheck(id: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/monitors/${id}/check`, { method: "POST" });
}

// ── Alerts ────────────────────────────────────────────────────────

export function fetchAlerts(params?: {
  severity?: string;
  acknowledged?: boolean;
  limit?: number;
}): Promise<AlertItem[]> {
  const sp = new URLSearchParams();
  if (params?.severity) sp.set("severity", params.severity);
  if (params?.acknowledged !== undefined) sp.set("acknowledged", String(params.acknowledged));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<AlertItem[]>(`/api/alerts${qs ? `?${qs}` : ""}`);
}

export function acknowledgeAlert(id: string): Promise<AlertItem> {
  return request<AlertItem>(`/api/alerts/${id}/acknowledge`, { method: "PUT" });
}

export function fetchUnreadAlertCount(): Promise<{ unread: number }> {
  return request<{ unread: number }>("/api/alerts/unread");
}

// ── Live Feed ─────────────────────────────────────────────────────

export function fetchRecentEvents(limit: number = 50): Promise<Record<string, unknown>[]> {
  return request<Record<string, unknown>[]>(`/api/live-feed/recent?limit=${limit}`);
}

// ── Report Generation & Export ──────────────────────────────────────

export function createReport(data: {
  mission_id: string;
  report_type: string;
  config?: Record<string, unknown>;
}): Promise<ReportFull> {
  return request<ReportFull>("/reports/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// (Report CRUD, share, and export functions defined above)
