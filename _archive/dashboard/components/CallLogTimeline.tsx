"use client";

import { useState } from "react";
import type { CallLog } from "@/lib/types";

interface CallLogTimelineProps {
  logs: CallLog[];
}

const OUTCOME_STYLES: Record<string, string> = {
  connected: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  voicemail: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  no_answer: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  busy: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
  callback_scheduled: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
};

const DOT_COLORS: Record<string, string> = {
  connected: "bg-emerald-400",
  voicemail: "bg-blue-400",
  no_answer: "bg-amber-400",
  busy: "bg-amber-400",
  failed: "bg-red-400",
  callback_scheduled: "bg-indigo-400",
};

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === 0) return "--";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

function formatOutcome(outcome: string): string {
  return outcome.replace(/_/g, " ");
}

export default function CallLogTimeline({ logs }: CallLogTimelineProps) {
  if (logs.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
        <svg className="w-10 h-10 mx-auto text-gray-700 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
        </svg>
        <p className="text-sm text-gray-500">No call attempts yet.</p>
        <p className="text-xs text-gray-600 mt-1">
          Click &quot;Call Now&quot; to initiate the first call.
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-4 top-2 bottom-2 w-px bg-gray-800" />

      <div className="space-y-0">
        {logs.map((log, index) => (
          <CallLogEntry key={log.id} log={log} isLast={index === logs.length - 1} />
        ))}
      </div>
    </div>
  );
}

function CallLogEntry({ log, isLast }: { log: CallLog; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const outcome = log.outcome ?? "pending";
  const dotColor = DOT_COLORS[outcome] ?? "bg-gray-500";
  const outcomeStyle = OUTCOME_STYLES[outcome] ?? "bg-gray-500/10 text-gray-400 border-gray-500/20";
  const timestamp = log.started_at
    ? new Date(log.started_at).toLocaleString()
    : log.created_at
      ? new Date(log.created_at).toLocaleString()
      : "Unknown time";

  return (
    <div className={`relative pl-10 ${isLast ? "" : "pb-6"}`}>
      {/* Timeline dot */}
      <div className={`absolute left-2.5 top-1.5 w-3 h-3 rounded-full border-2 border-gray-950 ${dotColor}`} />

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        {/* Header row */}
        <div className="flex items-center justify-between gap-3 mb-2">
          <span className="text-xs text-gray-500">{timestamp}</span>
          <div className="flex items-center gap-2">
            {log.duration_sec !== null && log.duration_sec > 0 && (
              <span className="text-xs text-gray-400">
                {formatDuration(log.duration_sec)}
              </span>
            )}
            <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium capitalize ${outcomeStyle}`}>
              {formatOutcome(outcome)}
            </span>
          </div>
        </div>

        {/* Person reached */}
        {log.person_reached && (
          <p className="text-sm text-gray-300 mb-2">
            <span className="text-gray-500">Reached:</span> {log.person_reached}
          </p>
        )}

        {/* Summary */}
        {log.summary && (
          <p className="text-sm text-gray-400 leading-relaxed mb-2">{log.summary}</p>
        )}

        {/* Recording link */}
        {log.recording_url && (
          <a
            href={log.recording_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors mb-2"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
            </svg>
            Listen to recording
          </a>
        )}

        {/* Transcript toggle */}
        {log.transcript && (
          <div className="mt-2 pt-2 border-t border-gray-800">
            <button
              onClick={() => setExpanded((prev) => !prev)}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              <svg
                className={`w-3.5 h-3.5 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
              {expanded ? "Hide transcript" : "Show transcript"}
            </button>
            {expanded && (
              <div className="mt-3 bg-gray-800/50 border border-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap font-mono">
                  {log.transcript}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Next steps */}
        {log.next_steps && Object.keys(log.next_steps).length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-800">
            <p className="text-xs font-medium text-gray-400 mb-1">Next Steps</p>
            <div className="text-xs text-gray-500">
              {Object.entries(log.next_steps).map(([key, value]) => (
                <p key={key}>
                  <span className="text-gray-400 capitalize">{key.replace(/_/g, " ")}:</span>{" "}
                  {String(value)}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Twilio SID */}
        {log.twilio_call_sid && (
          <p className="text-xs text-gray-600 mt-2">SID: {log.twilio_call_sid}</p>
        )}
      </div>
    </div>
  );
}
