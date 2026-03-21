"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import {
  fetchMissionStatus,
  fetchMissionFindings,
  startMission,
  stopMission,
  rerunMission,
} from "@/lib/api";
import type {
  MissionLiveStatus,
  MissionFinding,
  MissionActivity,
  CrewAgent,
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

// ── Confidence badge ────────────────────────────────────────────────

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? "bg-green-100 text-green-800" :
    pct >= 60 ? "bg-yellow-100 text-yellow-800" :
    "bg-red-100 text-red-800";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {pct}%
    </span>
  );
}

// ── Main Page ───────────────────────────────────────────────────────

export default function MissionDetailPage() {
  const params = useParams();
  const missionId = params.missionId as string;

  const [status, setStatus] = useState<MissionLiveStatus | null>(null);
  const [findings, setFindings] = useState<MissionFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"activity" | "findings" | "structured">("activity");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [actionLoading, setActionLoading] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);

  // Load mission status and findings
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

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll when mission is running (5s interval, skip if tab hidden)
  useEffect(() => {
    if (!status || !["running", "queued"].includes(status.status)) return;
    const interval = setInterval(() => {
      if (!document.hidden) loadData();
    }, 5000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- status?.status is the correct narrow dependency
  }, [status?.status, loadData]);

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
  const filteredFindings = categoryFilter
    ? findings.filter((f) => f.category === categoryFilter)
    : findings;
  const categories = [...new Set(findings.map((f) => f.category))];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* ── Mission Header ──────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">Mission</h1>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-medium text-white ${
                STATUS_COLORS[status.status] || "bg-gray-500"
              }`}
            >
              {status.status}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {status.findings_count} findings
            {status.confidence_score != null &&
              ` \u00b7 ${Math.round(status.confidence_score * 100)}% confidence`}
          </p>
        </div>

        {/* ── Actions ──────────────────────────────────────────────── */}
        <div className="flex gap-2">
          {isDraft && (
            <button
              onClick={handleStart}
              disabled={actionLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
            >
              {actionLoading ? "Starting..." : "Start Research"}
            </button>
          )}
          {isRunning && (
            <button
              onClick={handleStop}
              disabled={actionLoading}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 text-sm font-medium"
            >
              {actionLoading ? "Stopping..." : "Stop"}
            </button>
          )}
          {isDone && (
            <button
              onClick={handleRerun}
              disabled={actionLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
            >
              {actionLoading ? "Starting..." : "Re-run"}
            </button>
          )}
        </div>
      </div>

      {/* ── Expert Crew Panel ───────────────────────────────────────── */}
      {status.crew && status.crew.agents.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Expert Crew</h2>
          <div className="flex flex-wrap gap-3">
            {status.crew.agents.map((agent: CrewAgent) => (
              <div
                key={agent.agent_id}
                className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border"
              >
                <span className="text-lg">{agent.icon || "\U0001f916"}</span>
                <div>
                  <div className="text-sm font-medium text-gray-900">{agent.name}</div>
                  <div className="text-xs text-gray-500">{agent.role}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tabs ────────────────────────────────────────────────────── */}
      <div className="border-b">
        <nav className="flex gap-6">
          {(["activity", "findings", "structured"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
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
          className="bg-gray-900 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm"
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
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
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
                      ? "bg-blue-100 text-blue-800"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
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
                  className="bg-white border rounded-lg p-4 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-sm font-semibold text-gray-900 line-clamp-2">
                      {finding.title}
                    </h3>
                    <ConfidenceBadge value={finding.confidence} />
                  </div>
                  <p className="text-sm text-gray-600 line-clamp-3 mb-3">
                    {finding.content}
                  </p>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <div className="flex items-center gap-2">
                      <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                        {finding.category}
                      </span>
                      {finding.source_type && (
                        <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
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
                          className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded text-xs"
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
        <div className="bg-white border rounded-lg overflow-hidden">
          {findings.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No data points yet</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Title
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Category
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Confidence
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Source
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Content
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {findings.map((f) => (
                    <tr key={f.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 max-w-[200px] truncate">
                        {f.title}
                      </td>
                      <td className="px-4 py-3">
                        <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs">
                          {f.category}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <ConfidenceBadge value={f.confidence} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 max-w-[150px] truncate">
                        {f.source_name || f.source_url || "N/A"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 max-w-[300px] truncate">
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
    </div>
  );
}
