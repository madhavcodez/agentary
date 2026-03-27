"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchRecommendationInbox,
  fetchRecommendations,
  acceptRecommendation,
  rejectRecommendation,
  fetchInsightEvidence,
  createAction,
  fetchProjects,
} from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { IntelRecommendation, EvidenceItem } from "@/lib/types";
import Badge from "@/components/ui/Badge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import Tabs from "@/components/ui/Tabs";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import Dialog from "@/components/ui/Dialog";

// ── Priority config ──────────────────────────────────────────────────

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

// ── Tab config ───────────────────────────────────────────────────────

const TAB_LIST = [
  { id: "pending", label: "Pending" },
  { id: "accepted", label: "Accepted" },
  { id: "rejected", label: "Rejected" },
  { id: "all", label: "All" },
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Confidence bar ───────────────────────────────────────────────────

function ConfidenceBar({ confidence }: { confidence: number | null }) {
  if (confidence === null) return null;
  const pct = Math.round(confidence * 100);
  const barColor =
    pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function RecommendationsPage() {
  const { toast } = useToast();

  const [recs, setRecs] = useState<IntelRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("pending");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Record<string, EvidenceItem[]>>({});
  const [evidenceLoading, setEvidenceLoading] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Reject dialog state
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectTargetId, setRejectTargetId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [rejectSubmitting, setRejectSubmitting] = useState(false);

  // Take Action dialog state
  const [actionDialogOpen, setActionDialogOpen] = useState(false);
  const [actionTargetRec, setActionTargetRec] = useState<IntelRecommendation | null>(null);
  const [actionType, setActionType] = useState("");
  const [actionTitle, setActionTitle] = useState("");
  const [actionDescription, setActionDescription] = useState("");
  const [actionSubmitting, setActionSubmitting] = useState(false);
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
    if (!projectId) {
      setRecs([]);
      setLoading(false);
      return;
    }
    try {
      let data: IntelRecommendation[];
      if (activeTab === "pending") {
        data = await fetchRecommendationInbox({ project_id: projectId });
      } else if (activeTab === "all") {
        data = await fetchRecommendations({ project_id: projectId });
      } else {
        data = await fetchRecommendations({ project_id: projectId, status: activeTab });
      }
      // Sort by priority
      const sorted = [...data].sort(
        (a, b) =>
          (PRIORITY_ORDER[a.priority] ?? 99) -
          (PRIORITY_ORDER[b.priority] ?? 99),
      );
      setRecs(sorted);
    } catch {
      toast("Failed to load recommendations", "error");
    } finally {
      setLoading(false);
    }
  }, [activeTab, projectId, toast]);

  useEffect(() => {
    setLoading(true);
    setExpandedId(null);
    load();
  }, [load]);

  const handleExpand = async (rec: IntelRecommendation) => {
    if (expandedId === rec.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(rec.id);

    // Load evidence from insight if available
    if (rec.insight_id && !evidence[rec.id]) {
      setEvidenceLoading(rec.id);
      try {
        const ev = await fetchInsightEvidence(rec.insight_id);
        setEvidence((prev) => ({ ...prev, [rec.id]: ev }));
      } catch {
        // Evidence not critical, silently fail
        setEvidence((prev) => ({ ...prev, [rec.id]: [] }));
      } finally {
        setEvidenceLoading(null);
      }
    }
  };

  const handleAccept = async (id: string) => {
    setActionLoading(id);
    try {
      const updated = await acceptRecommendation(id);
      // Optimistic update
      setRecs((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: updated.status } : r)),
      );
      toast("Recommendation accepted", "success");
    } catch {
      toast("Failed to accept recommendation", "error");
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
      const updated = await rejectRecommendation(rejectTargetId, rejectReason.trim());
      setRecs((prev) =>
        prev.map((r) =>
          r.id === rejectTargetId
            ? { ...r, status: updated.status, rejection_reason: rejectReason.trim() }
            : r,
        ),
      );
      toast("Recommendation rejected", "success");
      setRejectDialogOpen(false);
    } catch {
      toast("Failed to reject recommendation", "error");
    } finally {
      setRejectSubmitting(false);
    }
  };

  const handleOpenTakeAction = (rec: IntelRecommendation) => {
    const suggested = rec.suggested_action ?? {};
    setActionTargetRec(rec);
    setActionType(
      (suggested.action_type as string) ??
        (suggested.type as string) ??
        "update",
    );
    setActionTitle(
      (suggested.title as string) ?? rec.title,
    );
    setActionDescription(
      (suggested.description as string) ?? rec.rationale ?? "",
    );
    setActionDialogOpen(true);
  };

  const handleTakeActionSubmit = async () => {
    if (!actionTargetRec || !actionTitle.trim()) {
      toast("Title is required", "error");
      return;
    }
    setActionSubmitting(true);
    try {
      await createAction({
        project_id: actionTargetRec.project_id,
        action_type: actionType || "update",
        title: actionTitle.trim(),
        description: actionDescription.trim() || undefined,
        recommendation_id: actionTargetRec.id,
        entity_id: actionTargetRec.entity_id ?? undefined,
        confidence: actionTargetRec.confidence ?? undefined,
        priority: actionTargetRec.priority,
      });
      toast("Action created successfully", "success");
      setActionDialogOpen(false);
    } catch {
      toast("Failed to create action", "error");
    } finally {
      setActionSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Recommendations</h1>
        <p className="text-sm text-gray-500 mt-1">
          AI-generated recommendations sorted by priority
        </p>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={TAB_LIST}
        activeTab={activeTab}
        onChange={setActiveTab}
        className="mb-6"
      />

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
        </div>
      )}

      {/* Empty state */}
      {!loading && recs.length === 0 && (
        <EmptyState
          title={`No ${activeTab === "all" ? "" : activeTab + " "}recommendations`}
          description="Recommendations appear here when insights are analyzed and actionable items are identified."
        />
      )}

      {/* Recommendation cards */}
      {!loading && recs.length > 0 && (
        <div className="space-y-3">
          {recs.map((rec) => {
            const isExpanded = expandedId === rec.id;
            const isPending = rec.status === "pending";
            const priorityVariant = PRIORITY_VARIANT[rec.priority] ?? "neutral";

            return (
              <div key={rec.id}>
                <button
                  onClick={() => handleExpand(rec)}
                  className="w-full text-left bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Top row: badges */}
                      <div className="flex items-center gap-2 flex-wrap mb-2">
                        <Badge variant={priorityVariant} size="sm">
                          {rec.priority}
                        </Badge>
                        <Badge variant="neutral" size="sm">
                          {rec.recommendation_type}
                        </Badge>
                        {rec.status !== "pending" && (
                          <Badge
                            variant={rec.status === "accepted" ? "success" : "danger"}
                            size="sm"
                          >
                            {rec.status}
                          </Badge>
                        )}
                      </div>

                      {/* Title */}
                      <h3 className="text-sm font-semibold text-gray-100 mb-1">
                        {rec.title}
                      </h3>

                      {/* Rationale preview */}
                      {rec.rationale && (
                        <p className="text-xs text-gray-400 line-clamp-2 mb-3">
                          {rec.rationale}
                        </p>
                      )}

                      {/* Confidence bar */}
                      <div className="max-w-xs mb-2">
                        <ConfidenceBar confidence={rec.confidence} />
                      </div>

                      {/* Bottom info */}
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span>{formatDate(rec.created_at)}</span>
                        {rec.rejection_reason && (
                          <span className="text-red-400 truncate max-w-[200px]">
                            Rejected: {rec.rejection_reason}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Action buttons (pending tab) */}
                    {isPending && activeTab === "pending" && (
                      <div
                        className="flex flex-col gap-2 shrink-0"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => handleAccept(rec.id)}
                          disabled={actionLoading === rec.id}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                        >
                          {actionLoading === rec.id ? "..." : "Accept"}
                        </button>
                        <button
                          onClick={() => handleOpenReject(rec.id)}
                          className="px-3 py-1.5 bg-gray-800 hover:bg-red-900/40 text-gray-400 hover:text-red-400 rounded-lg text-xs font-medium transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    )}

                    {/* Take Action button (accepted recommendations) */}
                    {rec.status === "accepted" && (
                      <div
                        className="shrink-0"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => handleOpenTakeAction(rec)}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors"
                        >
                          Take Action
                        </button>
                      </div>
                    )}
                  </div>
                </button>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="ml-4 mt-2 border-l-2 border-gray-700 pl-4 pb-2 space-y-3">
                    {/* Full rationale */}
                    {rec.rationale && (
                      <div className="bg-gray-800/50 rounded-lg p-3">
                        <h4 className="text-xs font-semibold text-gray-300 mb-1 uppercase tracking-wider">
                          Rationale
                        </h4>
                        <p className="text-sm text-gray-300 whitespace-pre-wrap">
                          {rec.rationale}
                        </p>
                      </div>
                    )}

                    {/* Suggested action */}
                    {rec.suggested_action &&
                      Object.keys(rec.suggested_action).length > 0 && (
                        <div className="bg-gray-800/50 rounded-lg p-3">
                          <h4 className="text-xs font-semibold text-gray-300 mb-1 uppercase tracking-wider">
                            Suggested Action
                          </h4>
                          <pre className="text-xs text-gray-400 overflow-x-auto">
                            {JSON.stringify(rec.suggested_action, null, 2)}
                          </pre>
                        </div>
                      )}

                    {/* Evidence chain */}
                    <div>
                      <h4 className="text-xs font-semibold text-gray-300 mb-2 uppercase tracking-wider">
                        Evidence Chain
                      </h4>
                      {evidenceLoading === rec.id && (
                        <div className="flex items-center gap-2 py-2">
                          <Spinner size="sm" />
                          <span className="text-xs text-gray-500">Loading evidence...</span>
                        </div>
                      )}
                      {evidence[rec.id] && evidence[rec.id].length === 0 && (
                        <p className="text-xs text-gray-500">No evidence chain available.</p>
                      )}
                      {evidence[rec.id]?.map((ev) => (
                        <div
                          key={ev.id}
                          className="bg-gray-900 border border-gray-800 rounded-lg p-3 mb-2"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="info" size="sm">
                              {ev.evidence_type}
                            </Badge>
                            <span className="text-xs text-gray-400">
                              Weight: {ev.weight.toFixed(2)}
                            </span>
                          </div>
                          {ev.notes && (
                            <p className="text-xs text-gray-400">{ev.notes}</p>
                          )}
                          {ev.observation && (
                            <div className="mt-2 pl-3 border-l border-gray-700">
                              <p className="text-xs font-medium text-gray-300">
                                {ev.observation.subject}
                              </p>
                              {ev.observation.content && (
                                <p className="text-xs text-gray-500 mt-0.5">
                                  {ev.observation.content}
                                </p>
                              )}
                              {ev.observation.source_url && (
                                <a
                                  href={ev.observation.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-emerald-400 hover:text-emerald-300 mt-1 inline-block"
                                >
                                  {ev.observation.source_name ?? "View source"}
                                </a>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Confidence detail */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">Confidence:</span>
                      <ConfidenceBadge confidence={rec.confidence} />
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
        title="Reject Recommendation"
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
              placeholder="Why are you rejecting this recommendation?"
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

      {/* Take Action Dialog */}
      <Dialog
        open={actionDialogOpen}
        onClose={() => setActionDialogOpen(false)}
        title="Take Action"
      >
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Action Type
            </label>
            <select
              value={actionType}
              onChange={(e) => setActionType(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="update">Update</option>
              <option value="alert">Alert</option>
              <option value="workflow">Workflow</option>
              <option value="monitor">Monitor</option>
              <option value="call">Call</option>
              <option value="merge">Merge</option>
              <option value="escalate">Escalate</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Title
            </label>
            <input
              type="text"
              value={actionTitle}
              onChange={(e) => setActionTitle(e.target.value)}
              placeholder="Action title"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={actionDescription}
              onChange={(e) => setActionDescription(e.target.value)}
              rows={3}
              placeholder="Describe what this action should do..."
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 resize-none"
            />
          </div>
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Link
                href="/approvals"
                className="text-indigo-400 hover:text-indigo-300"
                onClick={() => setActionDialogOpen(false)}
              >
                View Approvals
              </Link>
              <span>|</span>
              <Link
                href="/actions"
                className="text-indigo-400 hover:text-indigo-300"
                onClick={() => setActionDialogOpen(false)}
              >
                View Actions
              </Link>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setActionDialogOpen(false)}
                className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleTakeActionSubmit}
                disabled={actionSubmitting || !actionTitle.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {actionSubmitting ? "Creating..." : "Create Action"}
              </button>
            </div>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
