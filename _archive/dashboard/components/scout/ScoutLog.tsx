"use client";

import type { ScoutPhaseState, ScoutStatus } from "@/lib/types";
import ScoutPhase from "./ScoutPhase";

interface ScoutLogProps {
  phases: ScoutPhaseState[];
  status: ScoutStatus;
  errorMessage: string;
}

export default function ScoutLog({ phases, status, errorMessage }: ScoutLogProps) {
  if (status === "idle" && phases.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center px-6">
          <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-gray-800/60 border border-gray-700/50 flex items-center justify-center">
            <svg className="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.348 14.652a3.75 3.75 0 010-5.304m5.304 0a3.75 3.75 0 010 5.304m-7.425 2.121a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.788m13.788 0c3.808 3.808 3.808 9.98 0 13.788M12 12h.008v.008H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
            </svg>
          </div>
          <p className="text-sm text-gray-400">Ready to scout</p>
          <p className="text-xs text-gray-600 mt-1">
            Select skills and click Start Scout to begin
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2 p-1">
      {phases.map((phase) => (
        <ScoutPhase key={phase.name} phase={phase} />
      ))}

      {status === "error" && errorMessage && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-lg px-4 py-3">
          <p className="text-xs text-red-400">{errorMessage}</p>
        </div>
      )}
    </div>
  );
}
