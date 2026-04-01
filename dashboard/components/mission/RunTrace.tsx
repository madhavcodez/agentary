"use client";

import { useState, useEffect } from "react";
import { fetchRunSteps } from "@/lib/api";
import type { RunStepItem } from "@/lib/types";

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

interface RunTraceProps {
  runId: string;
}

export default function RunTrace({ runId }: RunTraceProps) {
  const [expanded, setExpanded] = useState(false);
  const [steps, setSteps] = useState<RunStepItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!expanded) return;
    setLoading(true);
    fetchRunSteps(runId)
      .then(setSteps)
      .catch(() => setSteps([]))
      .finally(() => setLoading(false));
  }, [expanded, runId]);

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full px-5 py-4 flex items-center justify-between text-sm font-semibold text-gray-200 hover:bg-white/[0.03] transition-all duration-[180ms]"
      >
        <span>Run Trace</span>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform duration-[180ms] ${expanded ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {expanded && (
        <div className="border-t border-white/[0.06] px-5 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-gray-700 border-t-emerald-400" />
            </div>
          ) : steps.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-sm">
              No trace steps recorded yet
            </div>
          ) : (
            <div className="space-y-2">
              {steps.map((step) => (
                <div
                  key={step.id}
                  className={`flex items-center gap-3 px-4 py-3 glass-card rounded-xl ${
                    step.parent_step_id ? "ml-6 border-dashed" : ""
                  }`}
                >
                  <span
                    className={`inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                      STEP_STATUS_COLORS[step.status] || "bg-gray-400"
                    }`}
                  />
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
                  <span className="text-xs text-gray-400 whitespace-nowrap">
                    {formatDuration(step.duration_ms)}
                  </span>
                  {step.tokens_used != null && (
                    <span className="text-xs text-gray-500 whitespace-nowrap">
                      {step.tokens_used.toLocaleString()} tok
                    </span>
                  )}
                  {step.error && (
                    <span className="text-xs text-red-400 truncate max-w-[120px]" title={JSON.stringify(step.error)}>
                      {typeof step.error?.message === "string" ? step.error.message : "error"}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
