export interface WSEvent {
  event_type: string;
  correlation_id?: string;
  project_id?: string | null;
  mission_id?: string | null;
  run_id?: string | null;
  user_id?: string | null;
  data: Record<string, unknown>;
  timestamp: string;
}

// Event type constants matching backend EventType enum
export const EventTypes = {
  // Run lifecycle
  RUN_STATE_CHANGED: "run.state_changed",

  // Mission
  MISSION_CREATED: "mission.created",
  MISSION_STARTED: "mission.started",
  MISSION_COMPLETED: "mission.completed",
  MISSION_FAILED: "mission.failed",

  // Agent activity
  AGENT_THINKING: "agent.thinking",
  AGENT_SEARCHING: "agent.searching",
  AGENT_SCRAPING: "agent.scraping",
  AGENT_CALLING: "agent.calling",
  AGENT_ANALYZING: "agent.analyzing",
  AGENT_WRITING: "agent.writing",
  AGENT_FOUND_DATA: "agent.found_data",
  AGENT_FOUND_INSIGHT: "agent.found_insight",
  AGENT_ERROR: "agent.error",

  // Finding
  FINDING_CREATED: "finding.created",

  // Call
  CALL_STARTED: "call.started",
  CALL_CONNECTED: "call.connected",
  CALL_COMPLETED: "call.completed",
  CALL_FAILED: "call.failed",

  // Monitor
  MONITOR_TRIGGERED: "monitor.triggered",
  MONITOR_ALERT: "monitor.alert",

  // Report
  REPORT_GENERATING: "report.generating",
  REPORT_COMPLETED: "report.completed",
  REPORT_FAILED: "report.failed",
} as const;

export type EventType = (typeof EventTypes)[keyof typeof EventTypes];
