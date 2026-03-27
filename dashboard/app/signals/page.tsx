"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchSignals,
  fetchSignalObservations,
  createSignal,
  fetchProjects,
} from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { useWS } from "@/components/WebSocketProvider";
import type { Signal, Observation } from "@/lib/types";
import type { WSEvent } from "@/lib/types/events";
import Badge from "@/components/ui/Badge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import Dialog from "@/components/ui/Dialog";

// ── Source type border colors ────────────────────────────────────────

const SOURCE_BORDER_COLOR: Record<string, string> = {
  mission: "border-l-emerald-500",
  monitor: "border-l-blue-500",
  workflow: "border-l-purple-500",
  voice: "border-l-amber-500",
  user: "border-l-orange-500",
  api: "border-l-cyan-500",
  upload: "border-l-fuchsia-500",
  action_outcome: "border-l-indigo-500",
};

const SOURCE_BADGE_VARIANT: Record<string, "success" | "info" | "warning" | "danger" | "neutral"> = {
  mission: "success",
  monitor: "info",
  workflow: "neutral",
  voice: "warning",
  user: "warning",
  api: "info",
  upload: "neutral",
  action_outcome: "neutral",
};

// ── Signal type icons ────────────────────────────────────────────────

const SIGNAL_TYPE_ICON: Record<string, string> = {
  change_detected: "C",
  data_extracted: "D",
  threshold_breached: "!",
  pattern_found: "P",
  anomaly_detected: "A",
  user_flagged: "U",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Source type options ───────────────────────────────────────────────

const SOURCE_TYPE_OPTIONS = [
  { value: "", label: "All Sources" },
  { value: "mission", label: "Mission" },
  { value: "monitor", label: "Monitor" },
  { value: "workflow", label: "Workflow" },
  { value: "voice", label: "Voice" },
  { value: "user", label: "User" },
  { value: "api", label: "API" },
  { value: "upload", label: "Upload" },
  { value: "action_outcome", label: "Action Outcome" },
];

const SIGNAL_TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "change_detected", label: "Change Detected" },
  { value: "data_extracted", label: "Data Extracted" },
  { value: "threshold_breached", label: "Threshold Breached" },
  { value: "pattern_found", label: "Pattern Found" },
  { value: "anomaly_detected", label: "Anomaly Detected" },
  { value: "user_flagged", label: "User Flagged" },
];

export default function SignalsPage() {
  const { toast } = useToast();
  const { subscribe } = useWS();

  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [sourceFilter, setSourceFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [observations, setObservations] = useState<Record<string, Observation[]>>({});
  const [obsLoading, setObsLoading] = useState<string | null>(null);
  const [showFlagDialog, setShowFlagDialog] = useState(false);
  const [flagTitle, setFlagTitle] = useState("");
  const [flagContent, setFlagContent] = useState("");
  const [flagSubmitting, setFlagSubmitting] = useState(false);
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
      setSignals([]);
      setLoading(false);
      return;
    }
    try {
      const params: Record<string, string> = {};
      params.project_id = projectId;
      if (sourceFilter) params.source_type = sourceFilter;
      if (typeFilter) params.signal_type = typeFilter;
      params.limit = "100";
      const data = await fetchSignals(params);
      setSignals(data);
    } catch {
      toast("Failed to load signals", "error");
    } finally {
      setLoading(false);
    }
  }, [projectId, sourceFilter, typeFilter, toast]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  // Real-time signal updates via WebSocket
  useEffect(() => {
    const handleEvent = (event: WSEvent) => {
      if (
        event.event_type === "signal.created" ||
        event.event_type === "finding.created"
      ) {
        load();
      }
    };
    const unsub = subscribe("*", handleEvent);
    return unsub;
  }, [subscribe, load]);

  const handleExpand = async (signalId: string) => {
    if (expandedId === signalId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(signalId);

    if (!observations[signalId]) {
      setObsLoading(signalId);
      try {
        const obs = await fetchSignalObservations(signalId);
        setObservations((prev) => ({ ...prev, [signalId]: obs }));
      } catch {
        toast("Failed to load observations", "error");
      } finally {
        setObsLoading(null);
      }
    }
  };

  const handleFlagSignal = async () => {
    if (!projectId) {
      toast("Create a project first to flag a signal", "error");
      return;
    }
    if (!flagTitle.trim()) {
      toast("Title is required", "error");
      return;
    }
    setFlagSubmitting(true);
    try {
      await createSignal({
        project_id: projectId,
        source_type: "user",
        signal_type: "user_flagged",
        title: flagTitle.trim(),
        content: flagContent.trim() || undefined,
      });
      toast("Signal flagged", "success");
      setShowFlagDialog(false);
      setFlagTitle("");
      setFlagContent("");
      load();
    } catch {
      toast("Failed to create signal", "error");
    } finally {
      setFlagSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Signal Feed</h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time intelligence signals from all sources
          </p>
        </div>
        <button
          onClick={() => setShowFlagDialog(true)}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Flag Signal
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
        >
          {SOURCE_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
        >
          {SIGNAL_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-500 ml-auto">
          {signals.length} signals
        </span>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
        </div>
      )}

      {/* Empty state */}
      {!loading && signals.length === 0 && (
        <EmptyState
          title="No signals found"
          description="Signals will appear here as they are captured from missions, monitors, and other sources."
        />
      )}

      {/* Signal feed */}
      {!loading && signals.length > 0 && (
        <div className="space-y-3">
          {signals.map((signal) => {
            const isExpanded = expandedId === signal.id;
            const borderColor =
              SOURCE_BORDER_COLOR[signal.source_type] ?? "border-l-gray-600";
            const badgeVariant =
              SOURCE_BADGE_VARIANT[signal.source_type] ?? "neutral";

            return (
              <div key={signal.id}>
                <button
                  onClick={() => handleExpand(signal.id)}
                  className={`w-full text-left bg-gray-800/50 border border-gray-800 border-l-4 ${borderColor} rounded-xl p-4 hover:bg-gray-800/80 transition-colors`}
                >
                  <div className="flex items-start gap-3">
                    {/* Signal type icon */}
                    <div className="w-8 h-8 rounded-lg bg-gray-700/50 flex items-center justify-center text-xs font-bold text-gray-400 shrink-0 mt-0.5">
                      {SIGNAL_TYPE_ICON[signal.signal_type] ?? "S"}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-semibold text-gray-100 truncate">
                          {signal.title}
                        </h3>
                        {signal.is_processed && (
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" title="Processed" />
                        )}
                      </div>
                      {signal.content && (
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                          {signal.content}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <Badge variant={badgeVariant} size="sm">
                          {signal.source_type}
                        </Badge>
                        <Badge variant="neutral" size="sm">
                          {signal.signal_type}
                        </Badge>
                        <ConfidenceBadge confidence={signal.confidence} />
                        <span className="text-xs text-gray-500 ml-auto">
                          {formatDate(signal.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                </button>

                {/* Expanded: observations */}
                {isExpanded && (
                  <div className="ml-6 mt-2 border-l-2 border-gray-700 pl-4 pb-2 space-y-2">
                    {obsLoading === signal.id && (
                      <div className="flex items-center gap-2 py-3">
                        <Spinner size="sm" />
                        <span className="text-xs text-gray-500">Loading observations...</span>
                      </div>
                    )}
                    {observations[signal.id] && observations[signal.id].length === 0 && (
                      <p className="text-xs text-gray-500 py-2">No observations linked to this signal.</p>
                    )}
                    {observations[signal.id]?.map((obs) => (
                      <div
                        key={obs.id}
                        className="bg-gray-900 border border-gray-800 rounded-lg p-3"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="info" size="sm">
                            {obs.observation_type}
                          </Badge>
                          <span className="text-xs font-medium text-gray-200">
                            {obs.subject}
                          </span>
                          {obs.is_stale && (
                            <Badge variant="danger" size="sm">stale</Badge>
                          )}
                        </div>
                        {obs.content && (
                          <p className="text-xs text-gray-400 mt-1">{obs.content}</p>
                        )}
                        <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                          {obs.source_name && <span>{obs.source_name}</span>}
                          {obs.source_url && (
                            <a
                              href={obs.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-emerald-400 hover:text-emerald-300 truncate max-w-[200px]"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Source
                            </a>
                          )}
                          <span className="ml-auto">
                            {formatDate(obs.created_at)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Flag Signal Dialog */}
      <Dialog
        open={showFlagDialog}
        onClose={() => setShowFlagDialog(false)}
        title="Flag Signal"
      >
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Title
            </label>
            <input
              type="text"
              value={flagTitle}
              onChange={(e) => setFlagTitle(e.target.value)}
              placeholder="What did you observe?"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Details (optional)
            </label>
            <textarea
              value={flagContent}
              onChange={(e) => setFlagContent(e.target.value)}
              rows={3}
              placeholder="Additional context or details..."
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-emerald-500 resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => setShowFlagDialog(false)}
              className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleFlagSignal}
              disabled={flagSubmitting || !flagTitle.trim()}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {flagSubmitting ? "Flagging..." : "Flag Signal"}
            </button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
