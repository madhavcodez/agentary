"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import type { ScoutPhaseState } from "@/lib/types";
import Spinner from "@/components/ui/Spinner";

interface ScoutPhaseProps {
  phase: ScoutPhaseState;
}

export default function ScoutPhase({ phase }: ScoutPhaseProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-900/60 hover:bg-gray-900/80 transition-colors duration-150"
      >
        <div className="flex items-center gap-2.5">
          <PhaseStatusIcon status={phase.status} />
          <span className="text-sm font-medium text-gray-200">{phase.label}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {phase.events.length} {phase.events.length === 1 ? "event" : "events"}
          </span>
          <svg
            className={cn(
              "w-4 h-4 text-gray-500 transition-transform duration-200",
              expanded && "rotate-180",
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </div>
      </button>

      {expanded && phase.events.length > 0 && (
        <div className="px-4 py-2 space-y-1 max-h-48 overflow-y-auto">
          {phase.events.map((entry) => (
            <div
              key={entry.id}
              className="flex items-start gap-2 py-1 animate-fadeIn"
            >
              <LogTypeIndicator type={entry.type} />
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-300 truncate">{entry.message}</p>
                {entry.detail && (
                  <p className="text-[11px] text-gray-500 truncate">{entry.detail}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PhaseStatusIcon({ status }: { status: ScoutPhaseState["status"] }) {
  switch (status) {
    case "pending":
      return (
        <div className="w-4 h-4 rounded-full border border-gray-700 flex items-center justify-center">
          <div className="w-1.5 h-1.5 rounded-full bg-gray-600" />
        </div>
      );
    case "running":
      return <Spinner size="sm" />;
    case "done":
      return (
        <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      );
    case "error":
      return (
        <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      );
  }
}

function LogTypeIndicator({ type }: { type: string }) {
  const color =
    type === "error"
      ? "bg-red-400"
      : type === "scored"
        ? "bg-emerald-400"
        : type === "filter_match" || type === "filter"
          ? "bg-amber-400"
          : "bg-gray-500";

  return <div className={cn("w-1 h-1 rounded-full mt-1.5 shrink-0", color)} />;
}
