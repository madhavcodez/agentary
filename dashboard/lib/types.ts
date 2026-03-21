export interface Skill {
  id: string | null;
  name: string;
  category: string | null;
  years_experience: string | null;
  proficiency: string | null;
}

export interface Experience {
  id: string | null;
  company: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
  evidence: string | null;
}

export interface Preference {
  id: string | null;
  key: string;
  value: string;
}

export interface Profile {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  location: string | null;
  summary: string | null;
  skills: Skill[];
  experiences: Experience[];
  preferences: Preference[];
  created_at: string;
  updated_at: string;
}

export interface Opportunity {
  id: string;
  source: string;
  source_id: string;
  company: string;
  title: string;
  location: string | null;
  description: string | null;
  url: string | null;
  created_at: string;
}

export interface OpportunityList {
  items: Opportunity[];
  total: number;
  page: number;
  limit: number;
}

export interface Match {
  id: string;
  opportunity_id: string;
  profile_id: string;
  hard_filter_pass: string;
  semantic_score: number;
  llm_score: number;
  composite_score: number;
  rationale: string | null;
  status: string;
  pipeline_stage: string;
  stage_changed_at: string | null;
  opportunity: Opportunity | null;
  created_at: string;
}

export interface MatchList {
  items: Match[];
  total: number;
  page: number;
  limit: number;
}

export interface MatchAction {
  status: string;
}

export interface PolicyCreate {
  name: string;
  rules_json: Record<string, unknown> | unknown[];
  description: string | null;
  is_active: boolean;
}

export interface PolicyUpdate {
  name?: string | null;
  rules_json?: Record<string, unknown> | unknown[] | null;
  description?: string | null;
  is_active?: boolean | null;
}

export interface Policy {
  id: string;
  name: string;
  rules_json: Record<string, unknown> | unknown[];
  is_active: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Dossier {
  id: string;
  match_id: string;
  content_md: string;
  sections_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
  updated_at: string;
}

export interface HealthCheck {
  status: string;
  checks: Record<string, string>;
}

export interface ResumeUpload {
  resume_text: string;
}

export interface Contact {
  id: string;
  company: string;
  name: string | null;
  title: string | null;
  phone: string;
  email: string | null;
  source: string;
  opportunity_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactList {
  items: Contact[];
  total: number;
  page: number;
  limit: number;
}

export interface Campaign {
  id: string;
  match_id: string;
  contact_id: string;
  status: string;
  scheduled_at: string | null;
  priority: number;
  script_json: Record<string, unknown> | null;
  max_attempts: number;
  attempt_count: number;
  contact: Contact | null;
  match: MatchWithOpportunity | null;
  email_draft: string | null;
  email_subject: string | null;
  linkedin_msg: string | null;
  outreach_sequence: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface MatchWithOpportunity {
  id: string;
  composite_score: number;
  rationale: string | null;
  status: string;
  opportunity: Opportunity | null;
}

export interface CampaignList {
  items: Campaign[];
  total: number;
  page: number;
  limit: number;
}

export interface CallLog {
  id: string;
  campaign_id: string;
  twilio_call_sid: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_sec: number | null;
  outcome: string | null;
  person_reached: string | null;
  transcript: string | null;
  summary: string | null;
  recording_url: string | null;
  next_steps: Record<string, unknown> | null;
  created_at: string;
}

export interface ResearchResult {
  id: string;
  match_id: string;
  company_intel: Record<string, unknown>;
  contacts_found: Array<Record<string, unknown>>;
  sources_used: string[];
  quality_score: number;
  researched_at: string;
}

export interface AutopilotStatus {
  last_run: string | null;
  last_result: Record<string, unknown> | null;
  next_scheduled: string | null;
}

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

// ── Analytics ────────────────────────────────────────────────────────

export interface PipelineSummary {
  lead: number;
  contacted: number;
  aware: number;
  engaged: number;
  meeting: number;
  closed_won: number;
  closed_lost: number;
  paused: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
  conversion_rate: number;
}

export interface FunnelData {
  days: number;
  total_matches: number;
  stages: FunnelStage[];
  closed_lost: number;
  paused: number;
}

export interface ChannelPerformance {
  days: number;
  email: {
    sent: number;
    opened: number;
    replied: number;
    open_rate: number;
    reply_rate: number;
  };
  call: {
    attempted: number;
    connected: number;
    rate: number;
  };
}

export interface TimelineEntry {
  date: string;
  matches_found: number;
  emails_sent: number;
  calls_made: number;
}

export interface ActivityTimeline {
  days: number;
  granularity: string;
  timeline: TimelineEntry[];
}

export interface ScoreBucket {
  bucket: string;
  count: number;
}

export interface ScoreDistribution {
  buckets: ScoreBucket[];
}

// ── Scout ───────────────────────────────────────────────────────────

export type ScoutStatus = "idle" | "running" | "paused" | "complete" | "error" | "cancelled";
export type ScoutMode = "rank_all" | "strict_filter";

export interface ScoutJob {
  id: string;
  match_id: string;
  title: string;
  company: string;
  location: string;
  score: number;
  rationale: string;
}

export interface ScoutSourceEvent {
  source: string;
  status: "fetching" | "done" | "error";
  jobs_found?: number;
  error?: string;
}

export interface ScoutPhaseEvent {
  phase: string;
  status: "started" | "done";
  total_raw?: number;
  new_jobs?: number;
  stored?: number;
  mode?: string;
  to_score?: number;
  total?: number;
  scored?: number;
}

export interface ScoutFilterEvent {
  skill: string;
  matches: number;
}

export interface ScoutPhaseState {
  name: string;
  label: string;
  status: "pending" | "running" | "done" | "error";
  events: ScoutLogEntry[];
}

export interface ScoutLogEntry {
  id: string;
  timestamp: number;
  type: string;
  message: string;
  detail?: string;
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
