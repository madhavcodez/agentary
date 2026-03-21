import type {
  ActivityTimeline,
  AutopilotStatus,
  CallLog,
  Campaign,
  CampaignList,
  ChannelPerformance,
  Contact,
  ContactList,
  Dossier,
  FunnelData,
  HealthCheck,
  Match,
  MatchList,
  Opportunity,
  OpportunityList,
  PipelineSummary,
  Policy,
  PolicyCreate,
  PolicyUpdate,
  Profile,
  ReportFull,
  ReportList,
  ResearchResult,
  ScoreDistribution,
  ShareResponse,
  ActiveInfo,
  AlertItem,
  MonitorSummary,
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

// ── Profile ─────────────────────────────────────────────────────────

export function fetchProfile(): Promise<Profile> {
  return request<Profile>("/profile");
}

export function uploadResume(resumeText: string): Promise<Profile> {
  return request<Profile>("/profile/resume", {
    method: "POST",
    body: JSON.stringify({ resume_text: resumeText }),
  });
}

// ── Opportunities ───────────────────────────────────────────────────

export function fetchOpportunities(params: {
  page?: number;
  limit?: number;
  source?: string;
  search?: string;
}): Promise<OpportunityList> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.source) searchParams.set("source", params.source);
  if (params.search) searchParams.set("search", params.search);
  const qs = searchParams.toString();
  return request<OpportunityList>(`/opportunities${qs ? `?${qs}` : ""}`);
}

export function fetchOpportunity(id: string): Promise<Opportunity> {
  return request<Opportunity>(`/opportunities/${id}`);
}

// ── Matches ─────────────────────────────────────────────────────────

export function fetchMatches(params: {
  page?: number;
  limit?: number;
  status?: string;
  min_score?: number;
}): Promise<MatchList> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.status) searchParams.set("status", params.status);
  if (params.min_score !== undefined)
    searchParams.set("min_score", String(params.min_score));
  const qs = searchParams.toString();
  return request<MatchList>(`/matches${qs ? `?${qs}` : ""}`);
}

export function fetchMatch(id: string): Promise<Match> {
  return request<Match>(`/matches/${id}`);
}

export function updateMatchStatus(
  id: string,
  status: string,
): Promise<Match> {
  return request<Match>(`/matches/${id}/action`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

// ── Dossiers ────────────────────────────────────────────────────────

export function fetchDossier(matchId: string): Promise<Dossier> {
  return request<Dossier>(`/matches/${matchId}/dossier`);
}

export function generateDossier(matchId: string): Promise<Dossier> {
  return request<Dossier>(`/matches/${matchId}/dossier`, {
    method: "POST",
  });
}

// ── Policies ────────────────────────────────────────────────────────

export function fetchPolicies(): Promise<Policy[]> {
  return request<Policy[]>("/policies");
}

export function fetchPolicy(id: string): Promise<Policy> {
  return request<Policy>(`/policies/${id}`);
}

export function createPolicy(data: PolicyCreate): Promise<Policy> {
  return request<Policy>("/policies", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updatePolicy(
  id: string,
  data: PolicyUpdate,
): Promise<Policy> {
  return request<Policy>(`/policies/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deletePolicy(
  id: string,
): Promise<{ status: string }> {
  return request<{ status: string }>(`/policies/${id}`, {
    method: "DELETE",
  });
}

// ── Contacts ───────────────────────────────────────────────────────

export function fetchContacts(params: {
  page?: number;
  limit?: number;
  company?: string;
}): Promise<ContactList> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.company) searchParams.set("company", params.company);
  const qs = searchParams.toString();
  return request<ContactList>(`/contacts${qs ? `?${qs}` : ""}`);
}

export function createContact(data: {
  company: string;
  name?: string;
  title?: string;
  phone: string;
  email?: string;
  source?: string;
  opportunity_id?: string;
  notes?: string;
}): Promise<Contact> {
  return request<Contact>("/contacts", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateContact(
  id: string,
  data: Partial<Contact>,
): Promise<Contact> {
  return request<Contact>(`/contacts/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteContact(
  id: string,
): Promise<{ status: string }> {
  return request<{ status: string }>(`/contacts/${id}`, {
    method: "DELETE",
  });
}

// ── Campaigns ──────────────────────────────────────────────────────

export function fetchCampaigns(params: {
  page?: number;
  limit?: number;
  status?: string;
}): Promise<CampaignList> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return request<CampaignList>(`/campaigns${qs ? `?${qs}` : ""}`);
}

export function fetchCampaign(id: string): Promise<Campaign> {
  return request<Campaign>(`/campaigns/${id}`);
}

export function createCampaign(data: {
  match_id: string;
  contact_id: string;
  scheduled_at?: string;
}): Promise<Campaign> {
  return request<Campaign>("/campaigns", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function triggerCall(campaignId: string): Promise<Campaign> {
  return request<Campaign>(`/campaigns/${campaignId}/call-now`, {
    method: "POST",
  });
}

export function generateScript(campaignId: string): Promise<Campaign> {
  return request<Campaign>(`/campaigns/${campaignId}/generate-script`, {
    method: "POST",
  });
}

export function fetchCampaignLogs(campaignId: string): Promise<CallLog[]> {
  return request<CallLog[]>(`/campaigns/${campaignId}/logs`);
}

// ── Research ──────────────────────────────────────────────────────

export function triggerResearch(matchId: string): Promise<ResearchResult> {
  return request<ResearchResult>(`/research/${matchId}`, {
    method: "POST",
  });
}

export function getResearch(matchId: string): Promise<ResearchResult> {
  return request<ResearchResult>(`/research/${matchId}`);
}

// ── Autopilot ─────────────────────────────────────────────────────

export function runAutopilot(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/autopilot/run", {
    method: "POST",
  });
}

export function getAutopilotStatus(): Promise<AutopilotStatus> {
  return request<AutopilotStatus>("/autopilot/status");
}

// ── Outreach Package ──────────────────────────────────────────────

export function generateOutreachPackage(campaignId: string): Promise<Campaign> {
  return request<Campaign>(`/campaigns/${campaignId}/outreach-package`, {
    method: "POST",
  });
}

export function sendEmail(campaignId: string): Promise<Campaign> {
  return request<Campaign>(`/campaigns/${campaignId}/send-email`, {
    method: "POST",
  });
}

// ── Pipeline ─────────────────────────────────────────────────────

export function fetchPipelineSummary(): Promise<PipelineSummary> {
  return request<PipelineSummary>("/matches/pipeline-summary");
}

export function updateMatchStage(
  matchId: string,
  stage: string,
  trigger: string = "manual",
): Promise<Match> {
  return request<Match>(`/matches/${matchId}/stage`, {
    method: "PUT",
    body: JSON.stringify({ stage, trigger }),
  });
}

// ── Analytics ────────────────────────────────────────────────────

export function fetchFunnel(days: number = 30): Promise<FunnelData> {
  return request<FunnelData>(`/analytics/funnel?days=${days}`);
}

export function fetchChannelPerformance(days: number = 30): Promise<ChannelPerformance> {
  return request<ChannelPerformance>(`/analytics/channel-performance?days=${days}`);
}

export function fetchActivityTimeline(
  days: number = 30,
  granularity: string = "day",
): Promise<ActivityTimeline> {
  return request<ActivityTimeline>(
    `/analytics/activity-timeline?days=${days}&granularity=${granularity}`,
  );
}

export function fetchScoreDistribution(): Promise<ScoreDistribution> {
  return request<ScoreDistribution>("/analytics/score-distribution");
}

// ── Reports ──────────────────────────────────────────────────────────

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

export function fetchReports(params: {
  page?: number;
  limit?: number;
  project_id?: string;
}): Promise<ReportList> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.project_id) searchParams.set("project_id", params.project_id);
  const qs = searchParams.toString();
  return request<ReportList>(`/reports/${qs ? `?${qs}` : ""}`);
}

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
  return request<{ status: string }>(`/reports/${id}`, {
    method: "DELETE",
  });
}

export function regenerateReport(id: string): Promise<ReportFull> {
  return request<ReportFull>(`/reports/${id}/regenerate`, {
    method: "POST",
  });
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

export function createShareLink(
  reportId: string,
): Promise<ShareResponse> {
  return request<ShareResponse>(`/reports/${reportId}/share`, {
    method: "POST",
  });
}

export function revokeShareLink(
  reportId: string,
): Promise<{ status: string }> {
  return request<{ status: string }>(`/reports/${reportId}/share`, {
    method: "DELETE",
  });
}

export function fetchSharedReport(token: string): Promise<ReportFull> {
  const url = `${BASE_URL}/shared/reports/${token}`;
  return fetch(url, { cache: "no-store" }).then((res) => {
    if (!res.ok) throw new Error("Report not found");
    return res.json() as Promise<ReportFull>;
  });
}

// ── Export ───────────────────────────────────────────────────────────

export function exportFindingsCsvUrl(missionId: string, params?: Record<string, string>): string {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return `${BASE_URL}/export/missions/${missionId}/findings/csv${qs}`;
}

export function exportFindingsExcelUrl(missionId: string): string {
  return `${BASE_URL}/export/missions/${missionId}/findings/excel`;
}

export function exportFindingsJsonUrl(missionId: string): string {
  return `${BASE_URL}/export/missions/${missionId}/findings/json`;
}

// ── Monitors ──────────────────────────────────────────────────────

export function fetchMonitors(params?: {
  status?: string;
  project_id?: string;
}): Promise<MonitorSummary[]> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.project_id) sp.set("project_id", params.project_id);
  const qs = sp.toString();
  return request<MonitorSummary[]>(`/api/monitors${qs ? `?${qs}` : ""}`);
}

export function fetchMonitor(id: string): Promise<MonitorSummary> {
  return request<MonitorSummary>(`/api/monitors/${id}`);
}

export function createMonitor(data: {
  name: string;
  monitor_type: string;
  check_config?: Record<string, unknown>;
  alert_config?: Record<string, unknown>;
  schedule_cron?: string;
  timezone?: string;
  project_id?: string;
  description?: string;
}): Promise<MonitorSummary> {
  return request<MonitorSummary>("/api/monitors", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateMonitor(
  id: string,
  data: Partial<{
    name: string;
    monitor_type: string;
    check_config: Record<string, unknown>;
    alert_config: Record<string, unknown>;
    schedule_cron: string;
    timezone: string;
    description: string;
  }>,
): Promise<MonitorSummary> {
  return request<MonitorSummary>(`/api/monitors/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteMonitor(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/monitors/${id}`, { method: "DELETE" });
}

export function triggerMonitorCheck(id: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/monitors/${id}/check`, { method: "POST" });
}

export function pauseMonitor(id: string): Promise<MonitorSummary> {
  return request<MonitorSummary>(`/api/monitors/${id}/pause`, { method: "POST" });
}

export function resumeMonitor(id: string): Promise<MonitorSummary> {
  return request<MonitorSummary>(`/api/monitors/${id}/resume`, { method: "POST" });
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

export function fetchActiveInfo(): Promise<ActiveInfo> {
  return request<ActiveInfo>("/api/live-feed/active");
}

// ── Workflows ────────────────────────────────────────────────────────

import type {
  WorkflowData,
  WorkflowListData,
  WorkflowRun as WFRun,
  WorkflowRunList as WFRunList,
  WorkflowTemplate as WFTemplate,
} from "./types";

export function fetchWorkflows(params: {
  page?: number;
  limit?: number;
  status?: string;
  project_id?: string;
}): Promise<WorkflowListData> {
  const sp = new URLSearchParams();
  if (params.page) sp.set("page", String(params.page));
  if (params.limit) sp.set("limit", String(params.limit));
  if (params.status) sp.set("status", params.status);
  if (params.project_id) sp.set("project_id", params.project_id);
  const qs = sp.toString();
  return request<WorkflowListData>(`/workflows${qs ? `?${qs}` : ""}`);
}

export function fetchWorkflow(id: string): Promise<WorkflowData> {
  return request<WorkflowData>(`/workflows/${id}`);
}

export function createWorkflow(data: {
  name: string;
  description?: string;
  project_id?: string;
  nodes?: unknown[];
  edges?: unknown[];
  variables?: Record<string, unknown>;
  trigger_type?: string;
  trigger_config?: Record<string, unknown>;
  created_from?: string;
}): Promise<WorkflowData> {
  return request<WorkflowData>("/workflows", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateWorkflow(
  id: string,
  data: {
    name?: string;
    description?: string;
    nodes?: unknown[];
    edges?: unknown[];
    variables?: Record<string, unknown>;
    trigger_type?: string;
    trigger_config?: Record<string, unknown>;
  },
): Promise<WorkflowData> {
  return request<WorkflowData>(`/workflows/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteWorkflow(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/workflows/${id}`, { method: "DELETE" });
}

export function activateWorkflow(id: string): Promise<WorkflowData> {
  return request<WorkflowData>(`/workflows/${id}/activate`, { method: "POST" });
}

export function pauseWorkflow(id: string): Promise<WorkflowData> {
  return request<WorkflowData>(`/workflows/${id}/pause`, { method: "POST" });
}

export function triggerWorkflowRun(id: string): Promise<WFRun> {
  return request<WFRun>(`/workflows/${id}/run`, { method: "POST" });
}

export function fetchWorkflowRuns(
  workflowId: string,
  params?: { page?: number; limit?: number },
): Promise<WFRunList> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<WFRunList>(`/workflows/${workflowId}/runs${qs ? `?${qs}` : ""}`);
}

export function fetchWorkflowRun(workflowId: string, runId: string): Promise<WFRun> {
  return request<WFRun>(`/workflows/${workflowId}/runs/${runId}`);
}

export function validateWorkflowApi(id: string): Promise<{ valid: boolean; errors: string[] }> {
  return request<{ valid: boolean; errors: string[] }>(`/workflows/${id}/validate`, {
    method: "POST",
  });
}

export function createWorkflowFromTemplate(data: {
  template_id: string;
  variables: Record<string, unknown>;
  project_id?: string;
  name?: string;
}): Promise<WorkflowData> {
  return request<WorkflowData>("/workflows/from-template", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function createWorkflowFromDescription(data: {
  description: string;
  project_id?: string;
}): Promise<WorkflowData> {
  return request<WorkflowData>("/workflows/from-description", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchWorkflowTemplates(category?: string): Promise<WFTemplate[]> {
  const qs = category ? `?category=${category}` : "";
  return request<WFTemplate[]>(`/workflow-templates${qs}`);
}

export function fetchWorkflowTemplate(id: string): Promise<WFTemplate> {
  return request<WFTemplate>(`/workflow-templates/${id}`);
}
