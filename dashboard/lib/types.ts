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
