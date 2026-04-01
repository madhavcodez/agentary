"use client";

import { STATUS_COLORS } from "@/lib/constants";

interface Mission {
  id: string;
  title: string;
  status: string;
  project_id: string | null;
  created_at: string | null;
}

interface ActiveRun {
  id: string;
  crew_id: string;
  status: string;
  started_at: string | null;
}

interface ActiveMissionsProps {
  missions: Mission[];
  runs: ActiveRun[];
}

export default function ActiveMissions({ missions, runs }: ActiveMissionsProps) {
  return (
    <div className="rounded-xl">
      <div className="px-1 pb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-200">Active Missions</h2>
        <span className="text-xs px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/15 font-medium">
          {missions.length} active
        </span>
      </div>
      <div className="divide-y divide-white/[0.04] max-h-64 overflow-y-auto">
        {missions.length === 0 && runs.length === 0 && (
          <div className="px-5 py-8 text-center text-sm text-gray-500">
            No active missions
          </div>
        )}
        {missions.map((m) => (
          <div key={m.id} className="px-5 py-3.5 flex items-center gap-3 hover:bg-white/[0.02] transition-colors duration-[180ms]">
            <div
              className={`w-2 h-2 rounded-full shrink-0 ${STATUS_COLORS[m.status] ?? "bg-gray-500"}`}
            />
            <div className="min-w-0 flex-1">
              <div className="text-sm text-gray-200 truncate font-medium">{m.title}</div>
              <div className="text-xs text-gray-500 mt-0.5">
                {m.created_at
                  ? new Date(m.created_at).toLocaleString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : ""}
              </div>
            </div>
          </div>
        ))}
        {runs.map((r) => (
          <div key={r.id} className="px-5 py-3.5 flex items-center gap-3 hover:bg-white/[0.02] transition-colors duration-[180ms]">
            <div
              className={`w-2 h-2 rounded-full shrink-0 ${STATUS_COLORS[r.status] ?? "bg-gray-500"}`}
            />
            <div className="min-w-0 flex-1">
              <div className="text-sm text-gray-200 truncate">Crew Run</div>
              <div className="text-xs text-gray-500 mt-0.5">{r.status}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
