"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchMonitors,
  triggerMonitorCheck,
  pauseMonitor,
  resumeMonitor,
  deleteMonitor,
} from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { MonitorSummary } from "@/lib/types";
import MonitorCreateWizard from "@/components/dashboard/MonitorCreateWizard";

const STATUS_DOT: Record<string, string> = {
  active: "bg-emerald-400",
  paused: "bg-amber-400",
  archived: "bg-gray-500",
};

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MonitorsPage() {
  const { toast } = useToast();
  const [monitors, setMonitors] = useState<MonitorSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchMonitors();
      setMonitors(data);
    } catch {
      setMonitors([]);
      toast("Failed to load monitors", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRunNow = async (id: string) => {
    setActionLoading(id);
    try {
      await triggerMonitorCheck(id);
      toast("Monitor check triggered", "success");
    } catch {
      toast("Failed to run monitor check", "error");
    } finally {
      setActionLoading(null);
      load();
    }
  };

  const handleTogglePause = async (monitor: MonitorSummary) => {
    setActionLoading(monitor.id);
    try {
      if (monitor.status === "active") {
        await pauseMonitor(monitor.id);
        toast("Monitor paused", "success");
      } else {
        await resumeMonitor(monitor.id);
        toast("Monitor resumed", "success");
      }
    } catch {
      toast("Failed to update monitor", "error");
    } finally {
      setActionLoading(null);
      load();
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this monitor? This action cannot be undone.")) return;
    setActionLoading(id);
    try {
      await deleteMonitor(id);
      toast("Monitor deleted", "success");
    } catch {
      toast("Failed to delete monitor", "error");
    } finally {
      setActionLoading(null);
      load();
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-100">Monitors</h1>
        <button
          onClick={() => setShowWizard(true)}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          New Monitor
        </button>
      </div>

      {loading && (
        <div className="text-center py-16 text-gray-500 text-sm">Loading monitors...</div>
      )}

      {!loading && monitors.length === 0 && (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-16 text-center">
          <p className="text-gray-400">No monitors yet.</p>
          <p className="text-sm text-gray-500 mt-2">
            Set up your first automated check.
          </p>
        </div>
      )}

      {!loading && monitors.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {monitors.map((m) => {
            const isActioning = actionLoading === m.id;
            return (
              <div
                key={m.id}
                className="bg-gray-900 border border-gray-800/50 rounded-xl p-5 flex flex-col gap-4"
              >
                {/* Header */}
                <div className="flex items-start gap-3">
                  <div
                    className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${STATUS_DOT[m.status] ?? "bg-gray-500"}`}
                  />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-gray-100 truncate">
                      {m.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
                        {m.monitor_type}
                      </span>
                      <span className="text-xs text-gray-500 capitalize">{m.status}</span>
                    </div>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-sm font-medium text-gray-200">{m.total_checks}</div>
                    <div className="text-xs text-gray-500">Checks</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-200">{m.total_alerts}</div>
                    <div className="text-xs text-gray-500">Alerts</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 leading-snug">
                      {formatDate(m.last_check_at)}
                    </div>
                    <div className="text-xs text-gray-500">Last check</div>
                  </div>
                </div>

                {/* Schedule */}
                {m.schedule_cron && (
                  <div className="text-xs text-gray-500 font-mono bg-gray-800/50 rounded px-2 py-1">
                    {m.schedule_cron}
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2 pt-1 border-t border-gray-800/50">
                  <button
                    onClick={() => handleRunNow(m.id)}
                    disabled={isActioning || m.status === "archived"}
                    className="flex-1 text-xs py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 disabled:opacity-40 transition-colors"
                  >
                    Run Now
                  </button>
                  <button
                    onClick={() => handleTogglePause(m)}
                    disabled={isActioning || m.status === "archived"}
                    className="flex-1 text-xs py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 disabled:opacity-40 transition-colors"
                  >
                    {m.status === "active" ? "Pause" : "Resume"}
                  </button>
                  <button
                    onClick={() => handleDelete(m.id)}
                    disabled={isActioning}
                    className="text-xs py-1.5 px-3 rounded-lg bg-gray-800 hover:bg-red-900/40 text-gray-400 hover:text-red-400 disabled:opacity-40 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showWizard && (
        <MonitorCreateWizard
          onClose={() => setShowWizard(false)}
          onCreated={() => {
            setShowWizard(false);
            load();
          }}
        />
      )}
    </div>
  );
}
