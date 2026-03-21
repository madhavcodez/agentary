import type {
  ExpertAgent,
  Finding,
  HealthCheck,
  Mission,
  Monitor,
  Project,
  Report,
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
}): Promise<Workflow> {
  return request<Workflow>("/api/workflows", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Monitors ────────────────────────────────────────────────────────

export function fetchMonitors(params?: {
  project_id?: string;
  status?: string;
  page?: number;
  limit?: number;
}): Promise<Monitor[]> {
  const sp = new URLSearchParams();
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.status) sp.set("status", params.status);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return request<Monitor[]>(`/api/monitors${qs ? `?${qs}` : ""}`);
}

export function createMonitor(data: {
  project_id: string;
  name: string;
  monitor_type: string;
}): Promise<Monitor> {
  return request<Monitor>("/api/monitors", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
