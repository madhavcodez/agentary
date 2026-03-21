"use client";

import Link from "next/link";
import type { MonitorSummary } from "@/lib/types";

interface MonitorsPanelProps {
  monitors: MonitorSummary[];
}

const STATUS_INDICATOR: Record<string, { dot: string; label: string }> = {
  active: { dot: "bg-emerald-400", label: "Active" },
  paused: { dot: "bg-amber-400", label: "Paused" },
  archived: { dot: "bg-gray-500", label: "Archived" },
};

function hasRecentAlert(m: MonitorSummary): boolean {
  if (!m.last_change_at) return false;
  const ago = Date.now() - new Date(m.last_change_at).getTime();
  return ago < 24 * 60 * 60 * 1000; // within 24h
}

export default function MonitorsPanel({ monitors }: MonitorsPanelProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-200">Monitors</h2>
        <span className="text-xs text-gray-500">
          {monitors.filter((m) => m.status === "active").length} active
        </span>
      </div>
      <div className="divide-y divide-gray-800 max-h-48 overflow-y-auto">
        {monitors.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-gray-500">
            No monitors configured
          </div>
        )}
        {monitors.map((m) => {
          const alerting = hasRecentAlert(m);
          const si = STATUS_INDICATOR[m.status] ?? STATUS_INDICATOR.active;
          return (
            <div key={m.id} className="px-4 py-2.5 flex items-center gap-3">
              <div
                className={`w-2.5 h-2.5 rounded-full shrink-0 ${alerting ? "bg-red-500 animate-pulse" : si.dot}`}
              />
              <div className="min-w-0 flex-1">
                <div className="text-sm text-gray-200 truncate">{m.name}</div>
                <div className="text-xs text-gray-500">{m.monitor_type}</div>
              </div>
              <div className="text-xs text-gray-500">
                {alerting ? (
                  <span className="text-red-400 font-medium">ALERT</span>
                ) : (
                  "OK"
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
