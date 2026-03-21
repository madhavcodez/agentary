// ── Auth ─────────────────────────────────────────────────────────────

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

export interface HealthCheck {
  status: string;
  checks: Record<string, string>;
}

// ── Projects ────────────────────────────────────────────────────────

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  status: "active" | "archived" | "completed";
  project_type: string;
  domain_context: string | null;
  total_missions: number;
  total_findings: number;
  total_reports_generated: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectList {
  items: Project[];
  total: number;
  page: number;
  limit: number;
}

// ── Missions ────────────────────────────────────────────────────────

export interface Mission {
  id: string;
  project_id: string;
  user_id: string;
  name: string;
  description: string | null;
  objective: string | null;
  status: "draft" | "queued" | "running" | "paused" | "completed" | "failed";
  mission_type: string;
  instructions: string | null;
  parameters: Record<string, unknown> | null;
  findings_count: number;
  confidence_score: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MissionList {
  items: Mission[];
  total: number;
  page: number;
  limit: number;
}

// ── Expert Agents ───────────────────────────────────────────────────

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
  created_at: string;
}

// ── Findings ────────────────────────────────────────────────────────

export interface Finding {
  id: string;
  mission_id: string;
  project_id: string | null;
  expert_agent_id: string | null;
  finding_type: string;
  title: string;
  content: string | null;
  structured_data: Record<string, unknown> | null;
  source_url: string | null;
  source_name: string | null;
  confidence: number | null;
  tags: string[];
  created_at: string;
}

export interface FindingList {
  items: Finding[];
  total: number;
  page: number;
  limit: number;
}

// ── Reports ──────────────────────────────────────────────────────────

export type ReportType =
  | "research_report"
  | "market_analysis"
  | "property_report"
  | "competitive_intel"
  | "due_diligence"
  | "custom";

export type ReportStatus = "generating" | "ready" | "failed";

export interface ChartConfig {
  id: string;
  type: string;
  title: string;
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
      borderWidth?: number;
    }>;
  };
  options?: Record<string, unknown>;
}

export interface ReportSection {
  title: string;
  content_md: string;
  finding_ids?: string[];
  chart_configs?: ChartConfig[];
  order: number;
}

export interface ReportSource {
  name: string;
  url?: string;
  type?: string;
  access_date?: string;
}

export interface ReportSummary {
  id: string;
  user_id: string;
  project_id: string | null;
  mission_id: string | null;
  title: string;
  description: string | null;
  report_type: ReportType;
  status: ReportStatus;
  share_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReportFull extends ReportSummary {
  content_markdown: string | null;
  content_html: string | null;
  sections: ReportSection[] | null;
  executive_summary: string | null;
  methodology: string | null;
  sources: ReportSource[] | null;
  charts: ChartConfig[] | null;
  structured_data: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  format_config: Record<string, unknown> | null;
  share_token: string | null;
  pdf_url: string | null;
}

export interface ReportList {
  items: ReportSummary[];
  total: number;
  page: number;
  limit: number;
}

export interface ShareResponse {
  url: string;
  token: string;
}

// ── Dashboard / Live Feed ──────────────────────────────────────────

export interface LiveEvent {
  event_id: string;
  event_type: string;
  scope: "global" | "user" | "project";
  user_id: string | null;
  project_id: string | null;
  data: Record<string, unknown>;
  timestamp: number;
}

export interface MonitorSummary {
  id: string;
  user_id: string;
  project_id: string | null;
  name: string;
  description: string | null;
  monitor_type: string;
  status: "active" | "paused" | "archived";
  check_config: Record<string, unknown>;
  alert_config: Record<string, unknown>;
  schedule_cron: string | null;
  timezone: string;
  last_check_at: string | null;
  last_change_at: string | null;
  total_checks: number;
  total_alerts: number;
  created_at: string;
  updated_at: string;
}

export interface AlertItem {
  id: string;
  monitor_id: string;
  project_id: string | null;
  alert_type: string;
  title: string;
  message: string | null;
  severity: "info" | "warning" | "critical";
  data: Record<string, unknown> | null;
  acknowledged: boolean;
  acknowledged_at: string | null;
  delivered_channels: string[] | null;
  created_at: string;
}

export interface ActiveInfo {
  active_missions: Array<{
    id: string;
    title: string;
    status: string;
    project_id: string | null;
    created_at: string | null;
  }>;
  active_runs: Array<{
    id: string;
    crew_id: string;
    status: string;
    started_at: string | null;
  }>;
  connected_clients: number;
}

// ── Workflows ────────────────────────────────────────────────────────

export type WorkflowStatus = "draft" | "active" | "paused" | "archived";
export type WorkflowTriggerType = "manual" | "scheduled" | "event";
export type WorkflowCreatedFrom = "template" | "natural_language" | "visual_editor" | "api";
export type WorkflowNodeStatus = "pending" | "running" | "completed" | "failed";
export type WorkflowRunStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface WorkflowNodePosition {
  x: number;
  y: number;
}

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

export interface WorkflowTriggerConfig {
  cron?: string;
  timezone?: string;
  event_type?: string;
  conditions?: Record<string, unknown>;
}

export interface WorkflowData {
  id: string;
  project_id: string | null;
  user_id: string;
  name: string;
  description: string | null;
  status: WorkflowStatus;
  trigger_type: WorkflowTriggerType;
  trigger_config: WorkflowTriggerConfig | null;
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

// ── Research Engine Types ─────────────────────────────────────────────

export interface MissionFinding {
  id: string;
  category: string;
  title: string;
  content: string;
  structured_data: Record<string, unknown> | null;
  source_type: string | null;
  source_url: string | null;
  source_name: string | null;
  confidence: number;
  verified: boolean;
  tags: string[];
  created_at: string | null;
}

export interface MissionActivity {
  id: string;
  activity_type: string;
  content: string | null;
  metadata: Record<string, unknown> | null;
  confidence: number | null;
  created_at: string | null;
}

export interface CrewAgent {
  agent_id: string;
  slug: string;
  name: string;
  role: string;
  icon: string | null;
}

export interface MissionLiveStatus {
  mission_id: string;
  status: string;
  findings_count: number;
  confidence_score: number | null;
  crew: { agents: CrewAgent[] } | null;
  activities: MissionActivity[];
}

export interface ExpertAgentData {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  specialty: string | null;
  system_prompt: string | null;
  tools: string[];
  model_config: Record<string, unknown>;
  icon: string | null;
  color: string | null;
  is_system: boolean;
  is_active: boolean;
  created_at: string | null;
}

export interface CrewRunData {
  id: string;
  status: string;
  trigger_type: string;
  iteration: number;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  summary: string | null;
  metrics: Record<string, unknown> | null;
  created_at: string | null;
}

export interface CrewTaskLive {
  task_id: string;
  expert_name: string;
  expert_icon: string;
  status: string;
  findings_produced: number;
}

export interface CrewRunLiveData {
  run_status: string;
  tasks: CrewTaskLive[];
  activities: MissionActivity[];
  has_more: boolean;
}
