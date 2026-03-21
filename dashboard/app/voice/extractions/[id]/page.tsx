"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

// ── Types ────────────────────────────────────────────────────────────

interface VoiceExtraction {
  id: string;
  name: string;
  status: "draft" | "active" | "paused" | "completed";
  objective: string;
  persona_name: string | null;
  persona_role: string | null;
  persona_company: string | null;
  total_targets: number;
  calls_completed: number;
  successful_calls: number;
  data_points_extracted: number;
  created_at: string;
  updated_at: string;
}

interface TranscriptTurn {
  speaker: "agent" | "user";
  text: string;
  timestamp?: string;
}

interface ExtractedDataPoint {
  key: string;
  value: string;
  confidence: number;
}

interface CallRecord {
  id: string;
  session_id: string;
  target_name: string;
  target_phone: string;
  status: "pending" | "in_progress" | "completed" | "failed" | "no_answer";
  duration_seconds: number | null;
  confidence_score: number | null;
  transcript: TranscriptTurn[] | null;
  extracted_data: ExtractedDataPoint[] | null;
  created_at: string;
  updated_at: string;
}

interface CallRecordsResponse {
  items: CallRecord[];
  total: number;
}

// ── Constants ────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  active: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  paused: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

const CALL_STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  in_progress: "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse",
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
  no_answer: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

// ── Helpers ──────────────────────────────────────────────────────────

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === 0) return "--";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ");
}

function formatConfidence(score: number | null): string {
  if (score === null) return "--";
  return `${Math.round(score * 100)}%`;
}

function confidenceBadgeClass(confidence: number): string {
  if (confidence >= 0.8) {
    return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  }
  if (confidence >= 0.5) {
    return "bg-amber-500/10 text-amber-400 border-amber-500/20";
  }
  return "bg-red-500/10 text-red-400 border-red-500/20";
}

function computeProgress(extraction: VoiceExtraction): number {
  if (extraction.total_targets === 0) return 0;
  return Math.min(
    100,
    Math.round((extraction.calls_completed / extraction.total_targets) * 100),
  );
}

// ── Toast ────────────────────────────────────────────────────────────

function Toast({
  message,
  type,
  onClose,
}: {
  message: string;
  type: "success" | "error" | "info";
  onClose: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bg =
    type === "success"
      ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
      : type === "error"
        ? "bg-red-500/15 border-red-500/30 text-red-400"
        : "bg-blue-500/15 border-blue-500/30 text-blue-400";

  return (
    <div
      className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-xl border text-sm font-medium shadow-lg ${bg}`}
    >
      {message}
    </div>
  );
}

// ── Component ────────────────────────────────────────────────────────

export default function VoiceExtractionDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [extraction, setExtraction] = useState<VoiceExtraction | null>(null);
  const [callRecords, setCallRecords] = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [callsLoading, setCallsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCallId, setExpandedCallId] = useState<string | null>(null);
  const [batchExecuting, setBatchExecuting] = useState(false);
  const [reExtractingId, setReExtractingId] = useState<string | null>(null);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error" | "info";
  } | null>(null);

  const loadExtraction = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`http://localhost:8000/voice/sessions/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "Unknown error");
        throw new Error(`API ${res.status}: ${body}`);
      }
      const data: VoiceExtraction = await res.json();
      setExtraction(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch extraction",
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadCalls = useCallback(async () => {
    setCallsLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `http://localhost:8000/voice/sessions/${id}/calls`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "Unknown error");
        throw new Error(`API ${res.status}: ${body}`);
      }
      const data: CallRecordsResponse = await res.json();
      setCallRecords(data.items);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch call records",
      );
    } finally {
      setCallsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadExtraction();
    loadCalls();
  }, [loadExtraction, loadCalls]);

  async function handleExecuteBatch() {
    setBatchExecuting(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `http://localhost:8000/voice/batch/${id}/execute`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "Unknown error");
        throw new Error(`API ${res.status}: ${body}`);
      }
      setToast({ message: "Batch execution started", type: "success" });
      loadExtraction();
      loadCalls();
    } catch (err) {
      setToast({
        message:
          err instanceof Error ? err.message : "Failed to execute batch",
        type: "error",
      });
    } finally {
      setBatchExecuting(false);
    }
  }

  async function handleReExtract(callId: string) {
    setReExtractingId(callId);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `http://localhost:8000/voice/sessions/${id}/calls/${callId}/re-extract`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "Unknown error");
        throw new Error(`API ${res.status}: ${body}`);
      }
      setToast({ message: "Re-extraction started", type: "success" });
      loadCalls();
    } catch (err) {
      setToast({
        message:
          err instanceof Error ? err.message : "Failed to re-extract data",
        type: "error",
      });
    } finally {
      setReExtractingId(null);
    }
  }

  function toggleCallExpand(callId: string) {
    setExpandedCallId((prev) => (prev === callId ? null : callId));
  }

  // ── Loading State ──────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
        <p className="text-sm text-gray-500 mt-3">Loading extraction...</p>
      </div>
    );
  }

  if (error && !extraction) {
    return (
      <div className="max-w-4xl">
        <div className="mb-6">
          <Link
            href="/voice/extractions"
            className="text-sm text-gray-400 hover:text-gray-200 transition-colors flex items-center gap-1"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 19.5L8.25 12l7.5-7.5"
              />
            </svg>
            Back to Extractions
          </Link>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!extraction) return null;

  const progress = computeProgress(extraction);
  const statusStyle =
    STATUS_STYLES[extraction.status] ?? STATUS_STYLES.draft;

  return (
    <div className="max-w-6xl">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href="/voice/extractions"
          className="text-sm text-gray-400 hover:text-gray-200 transition-colors flex items-center gap-1"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15.75 19.5L8.25 12l7.5-7.5"
            />
          </svg>
          Back to Extractions
        </Link>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-gray-100">
              {extraction.name}
            </h1>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-md border text-xs font-medium capitalize ${statusStyle}`}
            >
              {extraction.status}
            </span>
          </div>
          {extraction.objective && (
            <p className="text-sm text-gray-400 max-w-2xl">
              {extraction.objective}
            </p>
          )}
          {extraction.persona_name && (
            <p className="text-xs text-gray-500 mt-2">
              Persona: {extraction.persona_name}
              {extraction.persona_role && ` - ${extraction.persona_role}`}
              {extraction.persona_company &&
                ` at ${extraction.persona_company}`}
            </p>
          )}
        </div>
        <button
          onClick={handleExecuteBatch}
          disabled={
            batchExecuting ||
            extraction.status === "completed"
          }
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {batchExecuting ? (
            <>
              <div className="w-4 h-4 border-2 border-indigo-300 border-t-transparent rounded-full animate-spin" />
              Executing...
            </>
          ) : (
            <>
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"
                />
              </svg>
              Execute Batch
            </>
          )}
        </button>
      </div>

      {/* Progress Bar */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-300">
            Overall Progress
          </span>
          <span className="text-sm text-gray-400">
            {extraction.calls_completed} / {extraction.total_targets} calls
          </span>
        </div>
        <div className="w-full h-3 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              extraction.status === "completed"
                ? "bg-emerald-500"
                : "bg-indigo-500"
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1.5">{progress}% complete</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            Total Calls
          </p>
          <p className="text-2xl font-bold text-gray-100">
            {extraction.calls_completed}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            of {extraction.total_targets} targets
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            Successful
          </p>
          <p className="text-2xl font-bold text-emerald-400">
            {extraction.successful_calls}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {extraction.calls_completed > 0
              ? `${Math.round(
                  (extraction.successful_calls /
                    extraction.calls_completed) *
                    100,
                )}% success rate`
              : "No calls yet"}
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            Data Points
          </p>
          <p className="text-2xl font-bold text-indigo-400">
            {extraction.data_points_extracted}
          </p>
          <p className="text-xs text-gray-500 mt-1">extracted from calls</p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Call Records */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-base font-semibold text-gray-200">
            Call Records
          </h2>
        </div>

        {callsLoading ? (
          <div className="text-center py-12">
            <div className="inline-block w-5 h-5 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
            <p className="text-sm text-gray-500 mt-3">Loading calls...</p>
          </div>
        ) : callRecords.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="w-10 h-10 mx-auto text-gray-700 mb-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z"
              />
            </svg>
            <p className="text-sm text-gray-500">No call records yet.</p>
            <p className="text-xs text-gray-600 mt-1">
              Execute a batch to start making calls.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Target Name
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Phone
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {callRecords.map((call) => {
                  const callStatusStyle =
                    CALL_STATUS_STYLES[call.status] ??
                    CALL_STATUS_STYLES.pending;
                  const isExpanded = expandedCallId === call.id;

                  return (
                    <CallRecordRow
                      key={call.id}
                      call={call}
                      callStatusStyle={callStatusStyle}
                      isExpanded={isExpanded}
                      onToggle={() => toggleCallExpand(call.id)}
                      onReExtract={() => handleReExtract(call.id)}
                      isReExtracting={reExtractingId === call.id}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Call Record Row (extracted for readability) ──────────────────────

function CallRecordRow({
  call,
  callStatusStyle,
  isExpanded,
  onToggle,
  onReExtract,
  isReExtracting,
}: {
  call: CallRecord;
  callStatusStyle: string;
  isExpanded: boolean;
  onToggle: () => void;
  onReExtract: () => void;
  isReExtracting: boolean;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="hover:bg-gray-800/40 transition-colors cursor-pointer"
      >
        <td className="px-6 py-4">
          <span className="text-sm font-medium text-gray-200">
            {call.target_name}
          </span>
        </td>
        <td className="px-6 py-4">
          <span className="text-sm text-gray-300 font-mono">
            {call.target_phone}
          </span>
        </td>
        <td className="px-6 py-4">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium capitalize ${callStatusStyle}`}
          >
            {formatStatus(call.status)}
          </span>
        </td>
        <td className="px-6 py-4 text-center">
          <span className="text-sm text-gray-300">
            {formatDuration(call.duration_seconds)}
          </span>
        </td>
        <td className="px-6 py-4 text-center">
          <span className="text-sm text-gray-300">
            {formatConfidence(call.confidence_score)}
          </span>
        </td>
        <td className="px-6 py-4 text-right">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            <svg
              className={`w-4 h-4 transition-transform ${
                isExpanded ? "rotate-180" : ""
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
              />
            </svg>
          </button>
        </td>
      </tr>

      {/* Expanded Detail */}
      {isExpanded && (
        <tr>
          <td colSpan={6} className="px-6 pb-6 pt-2">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5 space-y-5">
              {/* Transcript */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-300">
                    Transcript
                  </h3>
                </div>
                {call.transcript && call.transcript.length > 0 ? (
                  <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
                    {call.transcript.map((turn, idx) => (
                      <div
                        key={idx}
                        className={`flex ${
                          turn.speaker === "user"
                            ? "justify-end"
                            : "justify-start"
                        }`}
                      >
                        <div
                          className={`max-w-[80%] rounded-xl px-4 py-2.5 ${
                            turn.speaker === "user"
                              ? "bg-gray-700 text-gray-200"
                              : "bg-indigo-600/20 text-indigo-200 border border-indigo-500/20"
                          }`}
                        >
                          <p className="text-xs font-medium mb-0.5 opacity-60">
                            {turn.speaker === "user" ? "User" : "Agent"}
                          </p>
                          <p className="text-sm leading-relaxed">
                            {turn.text}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">
                    No transcript available.
                  </p>
                )}
              </div>

              {/* Extracted Data */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-300">
                    Extracted Data
                  </h3>
                  <button
                    onClick={onReExtract}
                    disabled={
                      isReExtracting || call.status !== "completed"
                    }
                    className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isReExtracting ? (
                      <>
                        <div className="w-3 h-3 border-2 border-gray-500 border-t-gray-300 rounded-full animate-spin" />
                        Re-extracting...
                      </>
                    ) : (
                      <>
                        <svg
                          className="w-3.5 h-3.5"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={1.5}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
                          />
                        </svg>
                        Re-extract
                      </>
                    )}
                  </button>
                </div>
                {call.extracted_data && call.extracted_data.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {call.extracted_data.map((dp, idx) => (
                      <div
                        key={idx}
                        className="bg-gray-900 border border-gray-700 rounded-lg p-3"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                            {dp.key}
                          </span>
                          <span
                            className={`inline-flex items-center px-1.5 py-0.5 rounded border text-[10px] font-medium ${confidenceBadgeClass(
                              dp.confidence,
                            )}`}
                          >
                            {Math.round(dp.confidence * 100)}%
                          </span>
                        </div>
                        <p className="text-sm text-gray-200">{dp.value}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">
                    No data extracted yet.
                  </p>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
