"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import {
  fetchMissionStatus,
  fetchMissionFindings,
  fetchRunSteps,
  startMission,
  stopMission,
  rerunMission,
} from "@/lib/api";
import { useWS } from "@/components/WebSocketProvider";
import { EventTypes } from "@/lib/types/events";
import type { WSEvent } from "@/lib/types/events";
import type {
  MissionLiveStatus,
  MissionFinding,
  MissionActivity,
  CrewAgent,
  RunStepItem,
} from "@/lib/types";

// ── Status badge colors ─────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-500",
  queued: "bg-yellow-500",
  running: "bg-blue-500 animate-pulse",
  paused: "bg-orange-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

// ── Activity type icons ─────────────────────────────────────────────

const ACTIVITY_ICONS: Record<string, string> = {
  thinking: "\U0001f914",
  searching: "\U0001f50d",
  scraping: "\U0001f310",
  calling: "\U0001f4de",
  analyzing: "\U0001f4ca",
  writing: "\u270d\ufe0f",
  found_data: "\U0001f4cb",
  found_insight: "\U0001f4a1",
  error: "\u26a0\ufe0f",
  delegating: "\U0001f4e4",
  synthesizing: "\U0001f9e0",
};

// ── Run step status colors ──────────────────────────────────────────

const STEP_STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-500",
  failed: "bg-red-500",
  running: "bg-yellow-500 animate-pulse",
};

function formatDuration(ms: number | null): string {
  if (ms == null) return "--";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// ── Confidence badge ────────────────────────────────────────────────

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? "bg-emerald-500/15 text-emerald-300 border border-emerald-400/30" :
    pct >= 60 ? "bg-amber-500/15 text-amber-300 border border-amber-400/30" :
    "bg-rose-500/15 text-rose-300 border border-rose-400/30";
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${color}`}>
      {pct}%
    </span>
  );
}

// ── Main Page ───────────────────────────────────────────────────────

// Prefix patterns that match mission-related events
const MISSION_EVENT_PREFIXES = ["agent.", "mission.", "finding.", "run."];

function isMissionEvent(eventType: string): boolean {
  return MISSION_EVENT_PREFIXES.some((p) => eventType.startsWith(p));
}

export default function MissionDetailPage() {
  const params = useParams();
  const missionId = params.missionId as string;
  const { connectionState, subscribe } = useWS();

  const [status, setStatus] = useState<MissionLiveStatus | null>(null);
  const [findings, setFindings] = useState<MissionFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"activity" | "findings" | "structured">("activity");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [actionLoading, setActionLoading] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const disconnectedSinceRef = useRef<number | null>(null);

  // Run trace state
  const [traceExpanded, setTraceExpanded] = useState(false);
  const [traceSteps, setTraceSteps] = useState<RunStepItem[]>([]);
  const [traceLoading, setTraceLoading] = useState(false);

  // Load mission status and findings via REST
  const loadData = useCallback(async () => {
    try {
      const [statusData, findingsData] = await Promise.all([
        fetchMissionStatus(missionId),
        fetchMissionFindings(missionId),
      ]);
      setStatus(statusData);
      setFindings(findingsData.items);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load mission");
    } finally {
      setLoading(false);
    }
  }, [missionId]);

  // Initial REST fetch
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Re-fetch full state on WS reconnect
  useEffect(() => {
    if (connectionState === "connected") {
      disconnectedSinceRef.current = null;
      loadData();
    } else if (connectionState === "disconnected") {
      if (disconnectedSinceRef.current === null) {
        disconnectedSinceRef.current = Date.now();
      }
    }
  }, [connectionState, loadData]);

  // Subscribe to real-time events via WebSocket
  useEffect(() => {
    const handleEvent = (event: WSEvent) => {
      // Filter: only process events for this mission
      if (event.mission_id && event.mission_id !== missionId) return;

      if (!isMissionEvent(event.event_type)) return;

      // Mission state changes: update status from event data
      if (
        event.event_type === EventTypes.MISSION_COMPLETED ||
        event.event_type === EventTypes.MISSION_FAILED ||
        event.event_type === EventTypes.MISSION_STARTED ||
        event.event_type === EventTypes.RUN_STATE_CHANGED
      ) {
        loadData();
        return;
      }

      // Agent activity events: append to activities feed
      if (event.event_type.startsWith("agent.")) {
        const activityType = event.event_type.replace("agent.", "");
        const newActivity: MissionActivity = {
          id: event.correlation_id ?? `ws-${Date.now()}`,
          activity_type: activityType,
          content: (event.data.message as string) ?? (event.data.content as string) ?? activityType,
          metadata: event.data as Record<string, unknown>,
          confidence: (event.data.confidence as number) ?? null,
          created_at: event.timestamp,
        };
        setStatus((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            activities: [...prev.activities, newActivity],
          };
        });
      }

      // Finding events: refresh findings list
      if (event.event_type === EventTypes.FINDING_CREATED) {
        fetchMissionFindings(missionId)
          .then((data) => setFindings(data.items))
          .catch(() => {});
      }
    };

    const unsub = subscribe("*", handleEvent);
    return unsub;
  }, [missionId, subscribe, loadData]);

  // Fallback: poll if WS disconnected for >5s and mission is active
  useEffect(() => {
    if (connectionState !== "disconnected") return;
    if (!status || !["running", "queued"].includes(status.status)) return;

    const interval = setInterval(() => {
      if (
        disconnectedSinceRef.current !== null &&
        Date.now() - disconnectedSinceRef.current > 5000 &&
        !document.hidden
      ) {
        loadData();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [connectionState, status?.status, loadData]);

  // Fetch run steps when trace is expanded
  useEffect(() => {
    if (!traceExpanded || !status?.latest_run_id) return;
    setTraceLoading(true);
    fetchRunSteps(status.latest_run_id)
      .then((steps) => setTraceSteps(steps))
      .catch(() => setTraceSteps([]))
      .finally(() => setTraceLoading(false));
  }, [traceExpanded, status?.latest_run_id]);

  // Auto-scroll activity feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [status?.activities]);

  // Action handlers
  const handleStart = async () => {
    setActionLoading(true);
    try {
      await startMission(missionId);
      loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start");
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    setActionLoading(true);
    try {
      await stopMission(missionId);
      loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to stop");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRerun = async () => {
    setActionLoading(true);
    try {
      await rerunMission(missionId);
      loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to rerun");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!status) return null;

  const isRunning = ["running", "queued"].includes(status.status);
  const isDone = ["completed", "failed"].includes(status.status);
  const isDraft = status.status === "draft";
  const canStart = ["draft", "paused", "failed"].includes(status.status);
  const startLabel = status.status === "paused" ? "Resume Mission" : "Start Mission";
  const filteredFindings = categoryFilter
    ? findings.filter((f) => f.category === categoryFilter)
    : findings;
  const categories = [...new Set(findings.map((f) => f.category))];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6 text-gray-100">
      {/* ── Mission Header ──────────────────────────────────────────── */}
      <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0f172a]/90 to-[#090f1d]/90 p-6 shadow-[0_10px_40px_rgba(0,0,0,0.35)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-semibold tracking-tight text-white">Mission</h1>
              <span className="text-xs uppercase tracking-[0.2em] text-gray-400">Live Run Console</span>
            </div>
            <p className="text-sm text-gray-400 mt-2">
              Real-time mission operations, expert crew activity, and trace observability.
            </p>
            <div className="flex items-center gap-3 mt-4">
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium text-white ${
                STATUS_COLORS[status.status] || "bg-gray-500"
              }`}
            >
              {status.status}
            </span>
              <span className="text-xs text-gray-300">
                {status.findings_count} findings
                {status.confidence_score != null &&
                  ` · ${Math.round(status.confidence_score * 100)}% confidence`}
              </span>
            </div>
          </div>

        {/* ── Actions ──────────────────────────────────────────────── */}
          <div className="flex gap-2">
          {canStart && (
            <button
              onClick={handleStart}
              disabled={actionLoading}
              className="px-4 py-2.5 bg-white text-gray-950 rounded-xl hover:bg-gray-100 disabled:opacity-50 text-sm font-medium shadow-sm"
            >
              {actionLoading ? "Starting..." : startLabel}
            </button>
          )}
          {isRunning && (
            <button
              onClick={handleStop}
              disabled={actionLoading}
              className="px-4 py-2.5 bg-rose-500/90 text-white rounded-xl hover:bg-rose-500 disabled:opacity-50 text-sm font-medium"
            >
              {actionLoading ? "Stopping..." : "Stop"}
            </button>
          )}
          {isDone && (
            <button
              onClick={handleRerun}
              disabled={actionLoading}
              className="px-4 py-2.5 bg-indigo-500/90 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium"
            >
              {actionLoading ? "Starting..." : "Re-run"}
            </button>
          )}
          </div>
        </div>
      </div>

      {/* ── Expert Crew Panel ───────────────────────────────────────── */}
      {status.crew && status.crew.agents.length > 0 && (
        <div className="bg-[#0b1220] rounded-2xl border border-white/10 p-5">
          <h2 className="text-sm font-semibold text-gray-200 mb-4 tracking-wide uppercase">Expert Crew</h2>
          <div className="flex flex-wrap gap-3">
            {status.crew.agents.map((agent: CrewAgent) => (
              <div
                key={agent.agent_id}
                className="flex items-center gap-3 px-4 py-3 bg-white/[0.03] rounded-xl border border-white/10"
              >
                <span className="text-lg">{agent.icon || "\U0001f916"}</span>
                <div>
                  <div className="text-sm font-medium text-gray-100">{agent.name}</div>
                  <div className="text-xs text-gray-400">{agent.role}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tabs ────────────────────────────────────────────────────── */}
      <div className="border-b border-white/10">
        <nav className="flex gap-6">
          {(["activity", "findings", "structured"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-white text-white"
                  : "border-transparent text-gray-400 hover:text-gray-200"
              }`}
            >
              {tab === "activity" && "Live Activity"}
              {tab === "findings" && `Findings (${findings.length})`}
              {tab === "structured" && "Structured Data"}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Live Activity Feed ──────────────────────────────────────── */}
      {activeTab === "activity" && (
        <div
          ref={feedRef}
          className="bg-[#070d18] rounded-2xl border border-white/10 p-4 h-96 overflow-y-auto font-mono text-sm"
        >
          {status.activities.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              {isDraft ? "Start the mission to see live activity" : "No activity yet"}
            </div>
          ) : (
            <div className="space-y-1">
              {[...status.activities].reverse().map((activity: MissionActivity) => (
                <div key={activity.id} className="flex gap-2 text-gray-300">
                  <span className="text-gray-600 text-xs whitespace-nowrap">
                    {activity.created_at
                      ? new Date(activity.created_at).toLocaleTimeString()
                      : ""}
                  </span>
                  <span>
                    {ACTIVITY_ICONS[activity.activity_type] || "\u2022"}{" "}
                  </span>
                  <span className="text-gray-100">{activity.content}</span>
                </div>
              ))}
              {isRunning && (
                <div className="flex gap-2 text-blue-400 animate-pulse">
                  <span className="text-gray-600 text-xs whitespace-nowrap">
                    {new Date().toLocaleTimeString()}
                  </span>
                  <span>\u23f3</span>
                  <span>Researching...</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Findings Panel ──────────────────────────────────────────── */}
      {activeTab === "findings" && (
        <div className="space-y-4">
          {/* Filters */}
          {categories.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setCategoryFilter("")}
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  !categoryFilter
                    ? "bg-white text-gray-900"
                    : "bg-white/5 text-gray-300 hover:bg-white/10"
                }`}
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    categoryFilter === cat
                      ? "bg-white text-gray-900"
                      : "bg-white/5 text-gray-300 hover:bg-white/10"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}

          {/* Finding cards */}
          {filteredFindings.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No findings yet</div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredFindings.map((finding) => (
                <div
                  key={finding.id}
                  className="bg-[#0b1220] border border-white/10 rounded-2xl p-4 hover:border-white/20 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-sm font-semibold text-gray-100 line-clamp-2">
                      {finding.title}
                    </h3>
                    <ConfidenceBadge value={finding.confidence} />
                  </div>
                  <p className="text-sm text-gray-300 line-clamp-3 mb-3">
                    {finding.content}
                  </p>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <div className="flex items-center gap-2">
                      <span className="bg-white/10 text-gray-200 px-2 py-0.5 rounded">
                        {finding.category}
                      </span>
                      {finding.source_type && (
                        <span className="bg-white/10 text-gray-300 px-2 py-0.5 rounded">
                          {finding.source_type}
                        </span>
                      )}
                    </div>
                    {finding.source_url && (
                      <a
                        href={finding.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-700 truncate max-w-[150px]"
                      >
                        {finding.source_name || "Source"}
                      </a>
                    )}
                  </div>
                  {finding.tags && finding.tags.length > 0 && (
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {finding.tags.slice(0, 5).map((tag) => (
                        <span
                          key={tag}
                          className="bg-indigo-500/20 text-indigo-200 px-1.5 py-0.5 rounded text-xs"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Structured Data Tab ─────────────────────────────────────── */}
      {activeTab === "structured" && (
        <div className="bg-[#0b1220] border border-white/10 rounded-2xl overflow-hidden">
          {findings.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No data points yet</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-white/10">
                <thead className="bg-white/5">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                      Title
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                      Category
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                      Confidence
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                      Source
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                      Content
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {findings.map((f) => (
                    <tr key={f.id} className="hover:bg-white/5">
                      <td className="px-4 py-3 text-sm font-medium text-gray-100 max-w-[200px] truncate">
                        {f.title}
                      </td>
                      <td className="px-4 py-3">
                        <span className="bg-white/10 text-gray-200 px-2 py-0.5 rounded text-xs">
                          {f.category}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <ConfidenceBadge value={f.confidence} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400 max-w-[150px] truncate">
                        {f.source_name || f.source_url || "N/A"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300 max-w-[300px] truncate">
                        {f.content}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Run Trace (Observability) ─────────────────────────────────── */}
      {status.latest_run_id && (
        <div className="bg-[#0b1220] border border-white/10 rounded-2xl overflow-hidden">
          <button
            onClick={() => setTraceExpanded((prev) => !prev)}
            className="w-full px-4 py-3 flex items-center justify-between text-sm font-semibold text-gray-200 hover:bg-white/5 transition-colors"
          >
            <span>Run Trace</span>
            <span className="text-gray-500 text-xs uppercase tracking-wide">
              {traceExpanded ? "collapse" : "expand"}
            </span>
          </button>
          {traceExpanded && (
            <div className="border-t border-white/10 px-4 py-3">
              {traceLoading ? (
                <div className="flex items-center justify-center py-6">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
                </div>
              ) : traceSteps.length === 0 ? (
                <div className="text-center py-6 text-gray-500 text-sm">
                  No trace steps recorded yet
                </div>
              ) : (
                <div className="space-y-2">
                  {traceSteps.map((step) => (
                    <div
                      key={step.id}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg border border-white/10 bg-white/[0.02] ${
                        step.parent_step_id ? "ml-6 border-dashed" : ""
                      }`}
                    >
                      {/* Status dot */}
                      <span
                        className={`inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                          STEP_STATUS_COLORS[step.status] || "bg-gray-400"
                        }`}
                      />
                      {/* Step name */}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-100 truncate">
                          {step.step_name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {step.step_type}
                          {step.started_at &&
                            ` -- ${new Date(step.started_at).toLocaleTimeString()}`}
                        </div>
                      </div>
                      {/* Duration */}
                      <span className="text-xs text-gray-400 whitespace-nowrap">
                        {formatDuration(step.duration_ms)}
                      </span>
                      {/* Tokens */}
                      {step.tokens_used != null && (
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {step.tokens_used.toLocaleString()} tok
                        </span>
                      )}
                      {/* Error indicator */}
                      {step.error && (
                        <span className="text-xs text-red-600 truncate max-w-[120px]" title={JSON.stringify(step.error)}>
                          {(step.error as Record<string, unknown>).message as string ?? "error"}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
