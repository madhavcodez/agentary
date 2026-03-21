"use client";

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

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500",
  running: "bg-indigo-500 animate-pulse",
  pending: "bg-amber-500",
};

export default function ActiveMissions({ missions, runs }: ActiveMissionsProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-200">Active Missions</h2>
        <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400">
          {missions.length} active
        </span>
      </div>
      <div className="divide-y divide-gray-800 max-h-64 overflow-y-auto">
        {missions.length === 0 && runs.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-gray-500">
            No active missions
          </div>
        )}
        {missions.map((m) => (
          <div key={m.id} className="px-4 py-3 flex items-center gap-3">
            <div
              className={`w-2 h-2 rounded-full shrink-0 ${STATUS_COLORS[m.status] ?? "bg-gray-500"}`}
            />
            <div className="min-w-0 flex-1">
              <div className="text-sm text-gray-200 truncate">{m.title}</div>
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
          <div key={r.id} className="px-4 py-3 flex items-center gap-3">
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
