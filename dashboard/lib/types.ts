// ── Auth ──────────────────────────────────────────────────────────
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

// ── Projects ─────────────────────────────────────────────────────
export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  status: string;
  project_type: string;
  domain_context: string | null;
  total_missions: number;
  total_findings: number;
  total_calls_made: number;
  total_reports_generated: number;
  created_at: string;
  updated_at: string;
}

// ── Missions ─────────────────────────────────────────────────────
export interface Mission {
  id: string;
  project_id: string;
  user_id: string;
  name: string;
  description: string | null;
  objective: string | null;
  status: string;
  mission_type: string;
  findings_count: number;
  confidence_score: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ── Expert Agents ────────────────────────────────────────────────
export interface ExpertAgent {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  specialty: string;
  icon: string | null;
  color: string | null;
  is_system: boolean;
  is_active: boolean;
}

// ── Findings ─────────────────────────────────────────────────────
export interface Finding {
  id: string;
  project_id: string;
  mission_id: string | null;
  finding_type: string;
  title: string;
  content: string | null;
  source_type: string | null;
  source_url: string | null;
  confidence: number | null;
  verified: boolean;
  tags: string[];
  created_at: string;
}

// ── Reports ──────────────────────────────────────────────────────
export interface Report {
  id: string;
  project_id: string;
  title: string;
  report_type: string;
  status: string;
  executive_summary: string | null;
  created_at: string;
  updated_at: string;
}

// ── Voice Extractions ────────────────────────────────────────────
export interface VoiceExtraction {
  id: string;
  project_id: string;
  name: string;
  status: string;
  total_targets: number;
  calls_completed: number;
  calls_successful: number;
  data_points_extracted: number;
  created_at: string;
}

// ── Workflows ────────────────────────────────────────────────────

export type WorkflowStatus = "draft" | "active" | "paused" | "archived";
export type WorkflowTriggerType = "manual" | "scheduled" | "event";
export type WorkflowCreatedFrom = "template" | "natural_language" | "visual_editor" | "api";
export type WorkflowNodeStatus = "pending" | "running" | "completed" | "failed";
export type WorkflowRunStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface WorkflowNodePosition { x: number; y: number; }

export interface WorkflowNode {
  id: string;
  type: string;
  label: string;
  config: Record<string, unknown>;
  position: WorkflowNodePosition;
}

export interface WorkflowEdge {
  source_node_id: string;
  target_node_id: string;
  source_port?: string;
  target_port?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  category: string;
  is_template: boolean;
  version: number;
  created_at: string;
}

export interface WorkflowData {
  id: string;
  project_id: string | null;
  user_id: string;
  name: string;
  description: string | null;
  status: WorkflowStatus;
  trigger_type: WorkflowTriggerType;
  trigger_config: Record<string, unknown> | null;
  created_from: WorkflowCreatedFrom;
  template_id: string | null;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables: Record<string, unknown>;
  last_run_at: string | null;
  total_runs: number;
  avg_duration_seconds: number | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowListData {
  items: WorkflowData[];
  total: number;
  page: number;
  limit: number;
}

export interface WorkflowNodeResult {
  status: WorkflowNodeStatus;
  output?: unknown;
  error?: string;
  duration?: number;
  started_at?: string;
  completed_at?: string;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  user_id: string;
  status: WorkflowRunStatus;
  trigger_type: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  node_results: Record<string, WorkflowNodeResult>;
  output_data: Record<string, unknown> | null;
  findings_generated: number;
  error: Record<string, unknown> | null;
  created_at: string;
}

export interface WorkflowRunList {
  items: WorkflowRun[];
  total: number;
  page: number;
  limit: number;
}

export interface WorkflowVariableSchema {
  name: string;
  type: string;
  label: string;
  required: boolean;
  default?: unknown;
  description: string;
}

export interface WorkflowTemplate {
  id: string;
  user_id: string | null;
  name: string;
  description: string | null;
  category: string;
  tags: string[];
  nodes_template: WorkflowNode[];
  edges_template: WorkflowEdge[];
  variables_schema: WorkflowVariableSchema[];
  is_system: boolean;
  is_public: boolean;
  install_count: number;
  created_at: string;
  updated_at: string;
}

// ── Monitors ─────────────────────────────────────────────────────
export interface Monitor {
  id: string;
  project_id: string;
  name: string;
  status: string;
  monitor_type: string;
  last_checked_at: string | null;
  created_at: string;
}

export interface Alert {
  id: string;
  monitor_id: string;
  severity: string;
  title: string;
  content: string | null;
  acknowledged: boolean;
  created_at: string;
}

// ── Health ────────────────────────────────────────────────────────
export interface HealthCheck {
  status: string;
  checks: Record<string, string>;
}
