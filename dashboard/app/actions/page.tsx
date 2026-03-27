"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchActions } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { ActionRequest } from "@/lib/types";
import Badge from "@/components/ui/Badge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import Tabs from "@/components/ui/Tabs";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";

// ── Config ──────────────────────────────────────────────────────────

const TAB_LIST = [
  { id: "all", label: "All" },
  { id: "completed", label: "Completed" },
  { id: "failed", label: "Failed" },
  { id: "rejected", label: "Rejected" },
  { id: "cancelled", label: "Cancelled" },
];

const STATUS_VARIANT: Record<string, "success" | "danger" | "warning" | "neutral" | "info"> = {
  completed: "success",
  failed: "danger",
  rejected: "warning",
  cancelled: "neutral",
  executing: "info",
  pending_approval: "info",
  approved: "success",
  pending: "neutral",
};

const PRIORITY_VARIANT: Record<string, "danger" | "warning" | "info" | "neutral"> = {
  critical: "danger",
  high: "warning",
  medium: "info",
  low: "neutral",
};

const ACTION_TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "update", label: "Update" },
  { value: "alert", label: "Alert" },
  { value: "workflow", label: "Workflow" },
  { value: "monitor", label: "Monitor" },
  { value: "call", label: "Call" },
  { value: "merge", label: "Merge" },
  { value: "escalate", label: "Escalate" },
];

const ACTION_TYPE_COLOR: Record<string, string> = {
  update: "text-blue-400",
  alert: "text-orange-400",
  workflow: "text-purple-400",
  monitor: "text-emerald-400",
  call: "text-amber-400",
  merge: "text-indigo-400",
  escalate: "text-red-400",
};

const PAGE_SIZE = 20;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Main page ───────────────────────────────────────────────────────

export default function ActionsPage() {
  const { toast } = useToast();

  const [actions, setActions] = useState<ActionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("all");
  const [typeFilter, setTypeFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(async (append = false) => {
    try {
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset: append ? offset : 0,
      };
      if (activeTab !== "all") {
        params.status = activeTab;
      }
      if (typeFilter) {
        params.action_type = typeFilter;
      }

      const stringParams: Record<string, string> = {};
      for (const [k, v] of Object.entries(params)) {
        stringParams[k] = String(v);
      }

      const data = await fetchActions(stringParams);

      if (append) {
        setActions((prev) => [...prev, ...data]);
      } else {
        setActions(data);
      }
      setHasMore(data.length >= PAGE_SIZE);
    } catch {
      toast("Failed to load actions", "error");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [activeTab, typeFilter, offset, toast]);

  useEffect(() => {
    setLoading(true);
    setExpandedId(null);
    setOffset(0);
    setHasMore(true);
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, typeFilter]);

  const handleLoadMore = () => {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    setLoadingMore(true);
  };

  // Trigger load when offset changes (for load more)
  useEffect(() => {
    if (offset > 0) {
      load(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset]);

  const handleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Action History</h1>
        <p className="text-sm text-gray-500 mt-1">
          Complete log of all action requests and their outcomes
        </p>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={TAB_LIST}
        activeTab={activeTab}
        onChange={setActiveTab}
        className="mb-6"
      />

      {/* Filter bar */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
        >
          {ACTION_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-500 ml-auto">
          {actions.length} actions
        </span>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
        </div>
      )}

      {/* Empty state */}
      {!loading && actions.length === 0 && (
        <EmptyState
          title={`No ${activeTab === "all" ? "" : activeTab + " "}actions`}
          description="Actions will appear here as they are created and processed by the system."
        />
      )}

      {/* Actions table */}
      {!loading && actions.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Priority
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Confidence
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {actions.map((action) => {
                const isExpanded = expandedId === action.id;
                const statusVariant = STATUS_VARIANT[action.status] ?? "neutral";
                const priorityVariant = PRIORITY_VARIANT[action.priority] ?? "neutral";
                const typeColor = ACTION_TYPE_COLOR[action.action_type] ?? "text-gray-400";
                const isExecuting = action.status === "executing";

                return (
                  <tr key={action.id} className="group">
                    <td colSpan={6} className="p-0">
                      <button
                        onClick={() => handleExpand(action.id)}
                        className="w-full text-left hover:bg-gray-800/30 transition-colors"
                      >
                        <div className="flex items-center px-4 py-3">
                          {/* Type */}
                          <div className="w-[100px] shrink-0">
                            <span className={`text-xs font-medium ${typeColor}`}>
                              {action.action_type}
                            </span>
                          </div>
                          {/* Title */}
                          <div className="flex-1 min-w-0 px-4">
                            <span className="text-sm text-gray-200 truncate block">
                              {action.title}
                            </span>
                          </div>
                          {/* Status */}
                          <div className="w-[120px] shrink-0 px-4">
                            <Badge
                              variant={statusVariant}
                              size="sm"
                              className={isExecuting ? "animate-pulse" : ""}
                            >
                              {action.status}
                            </Badge>
                          </div>
                          {/* Priority */}
                          <div className="w-[90px] shrink-0 px-4">
                            <Badge variant={priorityVariant} size="sm">
                              {action.priority}
                            </Badge>
                          </div>
                          {/* Confidence */}
                          <div className="w-[100px] shrink-0 px-4">
                            <ConfidenceBadge confidence={action.confidence} />
                          </div>
                          {/* Created */}
                          <div className="w-[140px] shrink-0 text-right">
                            <span className="text-xs text-gray-500">
                              {formatDate(action.created_at)}
                            </span>
                          </div>
                        </div>
                      </button>

                      {/* Expanded detail */}
                      {isExpanded && (
                        <div className="px-4 pb-4">
                          <div className="ml-4 border-l-2 border-gray-700 pl-4 space-y-3">
                            {/* Description */}
                            {action.description && (
                              <div className="bg-gray-800/50 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-gray-300 mb-1 uppercase tracking-wider">
                                  Description
                                </h4>
                                <p className="text-sm text-gray-300 whitespace-pre-wrap">
                                  {action.description}
                                </p>
                              </div>
                            )}

                            {/* State transitions timeline */}
                            {action.state_transitions.length > 0 && (
                              <div className="bg-gray-800/50 rounded-lg p-3">
                                <h4 className="text-xs font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                                  State Transitions
                                </h4>
                                <div className="space-y-2">
                                  {action.state_transitions.map((t, i) => (
                                    <div key={i} className="flex items-start gap-3">
                                      <div className="flex flex-col items-center">
                                        <div className="w-2 h-2 rounded-full bg-gray-500 mt-1.5" />
                                        {i < action.state_transitions.length - 1 && (
                                          <div className="w-px h-4 bg-gray-700 mt-1" />
                                        )}
                                      </div>
                                      <div>
                                        <div className="flex items-center gap-2">
                                          {t.from && (
                                            <>
                                              <span className="text-xs text-gray-500">{t.from}</span>
                                              <span className="text-xs text-gray-600">&rarr;</span>
                                            </>
                                          )}
                                          <span className="text-xs font-medium text-gray-300">{t.to}</span>
                                        </div>
                                        {t.reason && (
                                          <p className="text-xs text-gray-500 mt-0.5">{t.reason}</p>
                                        )}
                                        <span className="text-[10px] text-gray-600">
                                          {new Date(t.timestamp).toLocaleString()}
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Parameters */}
                            {action.parameters &&
                              Object.keys(action.parameters).length > 0 && (
                                <div className="bg-gray-800/50 rounded-lg p-3">
                                  <h4 className="text-xs font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                                    Parameters
                                  </h4>
                                  <table className="w-full">
                                    <tbody>
                                      {Object.entries(action.parameters).map(([key, value]) => (
                                        <tr key={key} className="border-b border-gray-700/50 last:border-0">
                                          <td className="py-1.5 pr-4 text-xs font-medium text-gray-400 align-top w-1/4">
                                            {key}
                                          </td>
                                          <td className="py-1.5 text-xs text-gray-300">
                                            {typeof value === "object"
                                              ? JSON.stringify(value, null, 2)
                                              : String(value)}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Load More */}
          {hasMore && (
            <div className="border-t border-gray-800 px-4 py-3 flex justify-center">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="px-6 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {loadingMore ? (
                  <span className="flex items-center gap-2">
                    <Spinner size="sm" />
                    Loading...
                  </span>
                ) : (
                  "Load More"
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
