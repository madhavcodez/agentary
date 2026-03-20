"use client";

import Button from "@/components/ui/Button";
import type { AutopilotStatus } from "@/lib/types";

interface AutopilotControlProps {
  status: AutopilotStatus | null;
  running: boolean;
  onRun: () => void;
}

export default function AutopilotControl({
  status,
  running,
  onRun,
}: AutopilotControlProps) {
  return (
    <>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-lg font-semibold text-gray-200">
            AI Research & Autopilot
          </h2>
          {status?.last_run && (
            <p className="text-xs text-gray-500 mt-0.5">
              Last autopilot run:{" "}
              {new Date(status.last_run).toLocaleString()}
            </p>
          )}
        </div>
        <Button
          loading={running}
          onClick={onRun}
          className="bg-purple-600 hover:bg-purple-500"
          icon={
            !running ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
              </svg>
            ) : undefined
          }
        >
          {running ? "Running Autopilot..." : "Run Autopilot"}
        </Button>
      </div>

      {status?.last_result && (
        <div className="bg-purple-500/5 border border-purple-500/15 rounded-xl p-4 mb-5">
          <h3 className="text-xs font-medium text-purple-400 uppercase tracking-wider mb-2">
            Last Autopilot Run
          </h3>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(status.last_result).map(([key, value]) => (
              <div key={key}>
                <p className="text-[10px] text-gray-500 uppercase">
                  {key.replace(/_/g, " ")}
                </p>
                <p className="text-sm text-gray-300 font-medium">
                  {String(value)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
