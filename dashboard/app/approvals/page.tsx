"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchPendingActions,
  approveAction,
  rejectAction,
} from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { useWS } from "@/components/WebSocketProvider";
import type { ActionRequest } from "@/lib/types";
import type { WSEvent } from "@/lib/types/events";
import Badge from "@/components/ui/Badge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import Dialog from "@/components/ui/Dialog";

// ── Action type config ──────────────────────────────────────────────

const ACTION_TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  update: { color: "bg-blue-500", label: "UPD" },
  alert: { color: "bg-orange-500", label: "ALT" },
  workflow: { color: "bg-purple-500", label: "WFL" },
  monitor: { color: "bg-emerald-500", label: "MON" },
  call: { color: "bg-amber-500", label: "CAL" },
  merge: { color: "bg-indigo-500", label: "MRG" },
  escalate: { color: "bg-red-500", label: "ESC" },
};

const PRIORITY_VARIANT: Record<string, "danger" | "warning" | "info" | "neutral"> = {
  critical: "danger",
  high: "warning",
  medium: "info",
  low: "neutral",
};

const PRIORITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

// ── Time formatting ─────────────────────────────────────────────────

function formatTimeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

// ── Main page ───────────────────────────────────────────────────────

export default function ApprovalsPage() {
  const { toast } = useToast();
  const { subscribe } = useWS();

  const [actions, setActions] = useState<ActionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Reject dialog state
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectTargetId, setRejectTargetId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [rejectSubmitting, setRejectSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchPendingActions();
      const sorted = [...data].sort(
        (a, b) =>
          (PRIORITY_ORDER[a.priority] ?? 99) -
          (PRIORITY_ORDER[b.priority] ?? 99),
      );
      setActions(sorted);
    } catch {
      toast("Failed to load pending approvals", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  // WebSocket: refetch on new pending approval events
  useEffect(() => {
    const handleEvent = (event: WSEvent) => {
      if (event.event_type === "action.pending_approval") {
        load();
      }
    };
    const unsub = subscribe("*", handleEvent);
    return unsub;
  }, [subscribe, load]);

  const handleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const handleApprove = async (id: string) => {
    setActionLoading(id);
    try {
      await approveAction(id);
      // Optimistically remove from list
      setActions((prev) => prev.filter((a) => a.id !== id));
      toast("Action approved", "success");
    } catch {
      toast("Failed to approve action", "error");
    } finally {
      setActionLoading(null);
    }
  };

  const handleOpenReject = (id: string) => {
    setRejectTargetId(id);
    setRejectReason("");
    setRejectDialogOpen(true);
  };

  const handleRejectSubmit = async () => {
    if (!rejectTargetId || !rejectReason.trim()) {
      toast("Please provide a reason for rejection", "error");
      return;
    }
    setRejectSubmitting(true);
    try {
      await rejectAction(rejectTargetId, rejectReason.trim());
      // Optimistically remove from list
      setActions((prev) => prev.filter((a) => a.id !== rejectTargetId));
      toast("Action rejected", "success");
      setRejectDialogOpen(false);
    } catch {
      toast("Failed to reject action", "error");
    } finally {
      setRejectSubmitting(false);
    }
  };

  const getActionTypeConfig = (actionType: string) =>
    ACTION_TYPE_CONFIG[actionType] ?? { color: "bg-gray-500", label: actionType.slice(0, 3).toUpperCase() };

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Approvals</h1>
          <p className="text-sm text-gray-500 mt-1">
            Actions awaiting your review and approval
          </p>
        </div>
        <Link
          href="/actions"
          className="text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          View Action History
        </Link>
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
          icon={
            <svg className="w-12 h-12 text-emerald-500/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          title="No pending approvals"
          description="All caught up! Actions that require approval will appear here."
        />
      )}

      {/* Approval cards */}
      {!loading && actions.length > 0 && (
        <div className="space-y-3">
          {actions.map((action) => {
            const isExpanded = expandedId === action.id;
            const typeConfig = getActionTypeConfig(action.action_type);
            const priorityVariant = PRIORITY_VARIANT[action.priority] ?? "neutral";

            return (
              <div key={action.id}>
                <button
                  onClick={() => handleExpand(action.id)}
                  className="w-full text-left bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    {/* Action type icon */}
                    <div
                      className={`w-10 h-10 rounded-lg ${typeConfig.color}/15 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5`}
                      style={{ color: "inherit" }}
                    >
                      <span className={`${typeConfig.color.replace("bg-", "text-")}`}>
                        {typeConfig.label}
                      </span>
                    </div>

                    <div className="flex-1 min-w-0">
                      {/* Badges row */}
                      <div className="flex items-center gap-2 flex-wrap mb-2">
                        <Badge variant={priorityVariant} size="sm">
                          {action.priority}
                        </Badge>
                        <Badge variant="neutral" size="sm">
                          {action.action_type}
                        </Badge>
                        {action.requires_approval && (
                          <Badge variant="warning" size="sm">
                            requires approval
                          </Badge>
                        )}
                      </div>

                      {/* Title */}
                      <h3 className="text-sm font-semibold text-gray-100 mb-1">
                        {action.title}
                      </h3>

                      {/* Description preview */}
                      {action.description && (
                        <p className="text-xs text-gray-400 line-clamp-2 mb-2">
                          {action.description}
                        </p>
                      )}

                      {/* Bottom info */}
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <ConfidenceBadge confidence={action.confidence} />
                        {action.entity_id && (
                          <span className="text-gray-400">
                            Entity: {action.entity_id.slice(0, 8)}...
                          </span>
                        )}
                        <span className="ml-auto">{formatTimeAgo(action.created_at)}</span>
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div
                      className="flex flex-col gap-2 shrink-0"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => handleApprove(action.id)}
                        disabled={actionLoading === action.id}
                        className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                      >
                        {actionLoading === action.id ? "..." : "Approve"}
                      </button>
                      <button
                        onClick={() => handleOpenReject(action.id)}
                        className="px-4 py-1.5 bg-gray-800 hover:bg-red-900/40 text-gray-400 hover:text-red-400 rounded-lg text-xs font-medium transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </button>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="ml-4 mt-2 border-l-2 border-gray-700 pl-4 pb-2 space-y-3">
                    {/* Full description */}
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
                                  <td className="py-1.5 pr-4 text-xs font-medium text-gray-400 align-top">
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

                    {/* State transitions timeline */}
                    {action.state_transitions.length > 0 && (
                      <div className="bg-gray-800/50 rounded-lg p-3">
                        <h4 className="text-xs font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                          State Transitions
                        </h4>
                        <div className="space-y-2">
                          {action.state_transitions.map((t, i) => (
                            <div key={i} className="flex items-start gap-3">
                              <div className="w-2 h-2 rounded-full bg-gray-500 mt-1.5 shrink-0" />
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

                    {/* Linked recommendation */}
                    {action.recommendation_id && (
                      <div className="bg-gray-800/50 rounded-lg p-3">
                        <h4 className="text-xs font-semibold text-gray-300 mb-1 uppercase tracking-wider">
                          Linked Recommendation
                        </h4>
                        <Link
                          href="/recommendations"
                          className="text-xs text-emerald-400 hover:text-emerald-300"
                        >
                          View recommendation {action.recommendation_id.slice(0, 8)}...
                        </Link>
                      </div>
                    )}

                    {/* Confidence detail */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">Confidence:</span>
                      <ConfidenceBadge confidence={action.confidence} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Reject Dialog */}
      <Dialog
        open={rejectDialogOpen}
        onClose={() => setRejectDialogOpen(false)}
        title="Reject Action"
      >
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Reason for rejection
            </label>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              placeholder="Why are you rejecting this action?"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-red-500 resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => setRejectDialogOpen(false)}
              className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleRejectSubmit}
              disabled={rejectSubmitting || !rejectReason.trim()}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {rejectSubmitting ? "Rejecting..." : "Reject"}
            </button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
