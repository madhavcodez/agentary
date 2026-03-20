import type {
  AutopilotStatus,
  CallLog,
  Campaign,
  CampaignList,
  Contact,
  ContactList,
  Dossier,
  HealthCheck,
  Match,
  MatchList,
  Opportunity,
  OpportunityList,
  Policy,
  PolicyCreate,
  PolicyUpdate,
  Profile,
  ResearchResult,
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
