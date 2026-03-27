"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchPendingActions,
  fetchActions,
  fetchRecommendations,
  fetchHealth,
  fetchProjects,
} from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { ActionRequest, IntelRecommendation } from "@/lib/types";
import Spinner from "@/components/ui/Spinner";

// ── Types ───────────────────────────────────────────────────────────

interface HealthData {
  status: string;
  checks: Record<string, string>;
  circuit_breakers?: Record<string, {
    state: string;
    fail_count: number;
    fail_max: number;
  }>;
}

interface OperatorState {
  pendingActions: ActionRequest[];
  failedActions: ActionRequest[];
  staleRecommendations: IntelRecommendation[];
  escalations: ActionRequest[];
  health: HealthData | null;
  loading: boolean;
  healthError: boolean;
}

// ── Constants ───────────────────────────────────────────────────────

const REFRESH_INTERVAL_MS = 60000;

const DATA_SERVICES = [
  { key: "postgres", name: "PostgreSQL" },
  { key: "redis", name: "Redis" },
  { key: "qdrant", name: "Qdrant" },
];

const CB_STATE_CONFIG: Record<string, { dot: string; label: string }> = {
  closed: { dot: "bg-emerald-400", label: "Healthy" },
  open: { dot: "bg-red-400", label: "Failing" },
  half_open: { dot: "bg-amber-400", label: "Recovering" },
};

function formatTimeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ── Main page ───────────────────────────────────────────────────────

export default function OperatorConsolePage() {
  const { toast } = useToast();
  const [state, setState] = useState<OperatorState>({
    pendingActions: [],
    failedActions: [],
    staleRecommendations: [],
    escalations: [],
    health: null,
    loading: true,
    healthError: false,
  });
  const [projectId, setProjectId] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const projects = await fetchProjects();
        if (!cancelled) {
          setProjectId(projects[0]?.id ?? "");
        }
      } catch {
        if (!cancelled) {
          setProjectId("");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const load = useCallback(async () => {
    const recommendationPromise = projectId
      ? fetchRecommendations({ project_id: projectId, status: "pending", limit: 50 })
      : Promise.resolve([] as IntelRecommendation[]);
    const results = await Promise.allSettled([
      fetchPendingActions(projectId || undefined),
      fetchActions({ status: "failed", limit: 5 }),
      recommendationPromise,
      fetchActions({ action_type: "escalate", limit: 5 }),
      fetchHealth(),
    ]);

    const pendingActions =
      results[0].status === "fulfilled" ? results[0].value : [];
    const failedActions =
      results[1].status === "fulfilled" ? results[1].value : [];

    // Client-side stale approximation: recommendations pending for >24h
    const allRecs =
      results[2].status === "fulfilled" ? results[2].value : [];
    const staleRecommendations = allRecs.filter((r) => {
      const ageHours = (Date.now() - new Date(r.created_at).getTime()) / (1000 * 60 * 60);
      return ageHours > 24;
    });

    const escalations =
      results[3].status === "fulfilled" ? results[3].value : [];
    const health =
      results[4].status === "fulfilled"
        ? (results[4].value as HealthData)
        : null;
    const healthError = results[4].status === "rejected";

    if (healthError) {
      toast("Failed to fetch system health", "error");
    }

    setState({
      pendingActions,
      failedActions,
      staleRecommendations,
      escalations,
      health,
      loading: false,
      healthError,
    });
  }, [projectId, toast]);

  useEffect(() => {
    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  if (state.loading) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <h1 className="text-2xl font-bold text-gray-100 mb-6">Operator Console</h1>
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  const pendingCount = state.pendingActions.length;
  const failedCount = state.failedActions.length;
  const staleCount = state.staleRecommendations.length;
  const systemOk = state.health?.status === "ok";

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Operator Console</h1>
          <p className="text-sm text-gray-500 mt-1">
            System overview and operational status
          </p>
        </div>
        <span className="text-xs text-gray-600">
          Auto-refreshes every 30s
        </span>
      </div>

      {/* 2x3 Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Panel 1: Pending Approvals */}
        <div
          className={`bg-gray-900 border rounded-xl p-6 ${
            pendingCount > 0 ? "border-amber-500/30" : "border-gray-800"
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-200">Pending Approvals</h2>
            <div
              className={`w-2 h-2 rounded-full ${
                pendingCount > 0 ? "bg-amber-400 animate-pulse" : "bg-emerald-400"
              }`}
            />
          </div>
          <div className="mb-3">
            <span
              className={`text-4xl font-bold ${
                pendingCount > 0 ? "text-amber-400" : "text-emerald-400"
              }`}
            >
              {pendingCount}
            </span>
          </div>
          <p className="text-xs text-gray-500 mb-4">
            {pendingCount === 0
              ? "No actions awaiting approval"
              : `${pendingCount} action${pendingCount === 1 ? "" : "s"} awaiting approval`}
          </p>
          <Link
            href="/approvals"
            className="text-xs text-emerald-400 hover:text-emerald-300 font-medium transition-colors"
          >
            Go to Approvals &rarr;
          </Link>
        </div>

        {/* Panel 2: Failed Actions (24h) */}
        <div
          className={`bg-gray-900 border rounded-xl p-6 ${
            failedCount > 0 ? "border-red-500/30" : "border-gray-800"
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-200">Failed Actions (24h)</h2>
            <div
              className={`w-2 h-2 rounded-full ${
                failedCount > 0 ? "bg-red-400" : "bg-emerald-400"
              }`}
            />
          </div>
          <div className="mb-3">
            <span
              className={`text-4xl font-bold ${
                failedCount > 0 ? "text-red-400" : "text-emerald-400"
              }`}
            >
              {failedCount}
            </span>
          </div>
          {state.failedActions.length > 0 ? (
            <div className="space-y-2">
              {state.failedActions.slice(0, 5).map((a) => (
                <div key={a.id} className="flex items-center justify-between">
                  <span className="text-xs text-gray-400 truncate max-w-[200px]">
                    {a.title}
                  </span>
                  <span className="text-[10px] text-gray-600 shrink-0 ml-2">
                    {formatTimeAgo(a.created_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-500">No failed actions in the last 24 hours</p>
          )}
        </div>

        {/* Panel 3: Stale Recommendations */}
        <div
          className={`bg-gray-900 border rounded-xl p-6 ${
            staleCount > 0 ? "border-amber-500/30" : "border-gray-800"
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-200">Stale Recommendations</h2>
            <div
              className={`w-2 h-2 rounded-full ${
                staleCount > 0 ? "bg-amber-400" : "bg-emerald-400"
              }`}
            />
          </div>
          <div className="mb-3">
            <span
              className={`text-4xl font-bold ${
                staleCount > 0 ? "text-amber-400" : "text-emerald-400"
              }`}
            >
              {staleCount}
            </span>
          </div>
          <p className="text-xs text-gray-500 mb-4">
            {staleCount === 0
              ? "All recommendations are fresh"
              : `${staleCount} recommendation${staleCount === 1 ? "" : "s"} may need refresh`}
          </p>
          <Link
            href="/recommendations"
            className="text-xs text-emerald-400 hover:text-emerald-300 font-medium transition-colors"
          >
            View Recommendations &rarr;
          </Link>
        </div>

        {/* Panel 4: Queue Health */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-200">Queue Health</h2>
            <div
              className={`w-2 h-2 rounded-full ${
                state.healthError
                  ? "bg-red-400"
                  : systemOk
                    ? "bg-emerald-400"
                    : "bg-amber-400"
              }`}
            />
          </div>

          {state.healthError ? (
            <p className="text-xs text-red-400">Unable to reach health endpoint</p>
          ) : (
            <>
              {/* System status */}
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs text-gray-400">System Status</span>
                <span
                  className={`text-xs font-medium ${
                    systemOk ? "text-emerald-400" : "text-amber-400"
                  }`}
                >
                  {systemOk ? "Operational" : "Degraded"}
                </span>
              </div>

              {/* Data services */}
              <div className="space-y-2">
                {DATA_SERVICES.map((svc) => {
                  const ok = state.health?.checks?.[svc.key] === "ok";
                  return (
                    <div key={svc.key} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-1.5 h-1.5 rounded-full ${
                            ok ? "bg-emerald-400" : "bg-red-400"
                          }`}
                        />
                        <span className="text-xs text-gray-300">{svc.name}</span>
                      </div>
                      <span
                        className={`text-[10px] font-medium ${
                          ok ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {ok ? "Connected" : "Offline"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Panel 5: Connector Health */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-200">Connector Health</h2>
          </div>

          {state.healthError || !state.health?.circuit_breakers ? (
            <p className="text-xs text-gray-500">
              {state.healthError
                ? "Unable to fetch connector status"
                : "No circuit breaker data available"}
            </p>
          ) : (
            <div className="space-y-2">
              {Object.entries(state.health.circuit_breakers).map(
                ([name, cb]) => {
                  const config = CB_STATE_CONFIG[cb.state] ?? {
                    dot: "bg-gray-500",
                    label: cb.state,
                  };
                  return (
                    <div key={name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
                        <span className="text-xs text-gray-300 capitalize">
                          {name.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {cb.fail_count > 0 && (
                          <span className="text-[10px] text-amber-400">
                            {cb.fail_count}/{cb.fail_max}
                          </span>
                        )}
                        <span className={`text-[10px] font-medium ${config.dot.replace("bg-", "text-")}`}>
                          {config.label}
                        </span>
                      </div>
                    </div>
                  );
                },
              )}
            </div>
          )}
        </div>

        {/* Panel 6: Recent Escalations */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-200">Recent Escalations</h2>
            {state.escalations.length > 0 && (
              <div className="w-2 h-2 rounded-full bg-red-400" />
            )}
          </div>

          {state.escalations.length === 0 ? (
            <p className="text-xs text-gray-500">No recent escalations</p>
          ) : (
            <div className="space-y-2">
              {state.escalations.slice(0, 5).map((a) => {
                const statusColor =
                  a.status === "completed"
                    ? "text-emerald-400"
                    : a.status === "failed"
                      ? "text-red-400"
                      : "text-gray-400";
                return (
                  <div key={a.id} className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-gray-300 truncate block">
                        {a.title}
                      </span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-[10px] font-medium ${statusColor}`}>
                          {a.status}
                        </span>
                        <span className="text-[10px] text-gray-600">
                          {formatTimeAgo(a.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
