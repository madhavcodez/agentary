"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import MonitorCreateWizard from "@/components/dashboard/MonitorCreateWizard";
import {
  deleteMonitor,
  fetchMonitors,
  pauseMonitor,
  resumeMonitor,
  triggerMonitorCheck,
} from "@/lib/api";
import type { MonitorSummary } from "@/lib/types";

const STATUS_DOT: Record<string, string> = {
  active: "bg-emerald-400",
  paused: "bg-amber-400",
  archived: "bg-gray-500",
};

const TYPE_LABELS: Record<string, string> = {
  web_content: "Web Content",
  api_data: "API Data",
  price_tracker: "Price Tracker",
  listing_watcher: "Listing Watcher",
  competitor_tracker: "Competitor Tracker",
  custom: "Custom",
};

export default function MonitorsPage() {
  const [monitors, setMonitors] = useState<MonitorSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [checking, setChecking] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchMonitors();
      setMonitors(data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handlePause = async (id: string) => {
    await pauseMonitor(id);
    load();
  };

  const handleResume = async (id: string) => {
    await resumeMonitor(id);
    load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this monitor?")) return;
    await deleteMonitor(id);
    load();
  };

  const handleCheck = async (id: string) => {
    setChecking(id);
    try {
      await triggerMonitorCheck(id);
      load();
    } finally {
      setChecking(null);
    }
  };

  return (
    <>
      <Nav />
      <main className="ml-64 min-h-screen bg-gray-950 text-gray-100">
        <header className="sticky top-0 z-40 bg-gray-950/80 backdrop-blur-sm border-b border-gray-800">
          <div className="px-6 py-4 flex items-center justify-between">
            <h1 className="text-lg font-bold">Monitors</h1>
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium transition-colors"
            >
              + New Monitor
            </button>
          </div>
        </header>

        <div className="px-6 py-6">
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading...</div>
          ) : monitors.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">No monitors configured yet</p>
              <button
                onClick={() => setShowCreate(true)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm"
              >
                Create your first monitor
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {monitors.map((m) => (
                <div
                  key={m.id}
                  className="bg-gray-900 border border-gray-800 rounded-lg px-5 py-4 flex items-center gap-4"
                >
                  <div className={`w-3 h-3 rounded-full shrink-0 ${STATUS_DOT[m.status] ?? "bg-gray-500"}`} />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-gray-200">{m.name}</div>
                    <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-3">
                      <span>{TYPE_LABELS[m.monitor_type] ?? m.monitor_type}</span>
                      {m.schedule_cron && <span className="font-mono">{m.schedule_cron}</span>}
                      <span>{m.total_checks} checks</span>
                      <span>{m.total_alerts} alerts</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleCheck(m.id)}
                      disabled={checking === m.id}
                      className="px-3 py-1 text-xs border border-gray-700 rounded hover:bg-gray-800 text-gray-400 disabled:opacity-50"
                    >
                      {checking === m.id ? "Checking..." : "Run Now"}
                    </button>
                    {m.status === "active" ? (
                      <button
                        onClick={() => handlePause(m.id)}
                        className="px-3 py-1 text-xs border border-gray-700 rounded hover:bg-gray-800 text-amber-400"
                      >
                        Pause
                      </button>
                    ) : m.status === "paused" ? (
                      <button
                        onClick={() => handleResume(m.id)}
                        className="px-3 py-1 text-xs border border-gray-700 rounded hover:bg-gray-800 text-emerald-400"
                      >
                        Resume
                      </button>
                    ) : null}
                    <button
                      onClick={() => handleDelete(m.id)}
                      className="px-3 py-1 text-xs border border-gray-700 rounded hover:bg-gray-800 text-red-400"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {showCreate && (
          <MonitorCreateWizard
            onClose={() => setShowCreate(false)}
            onCreated={() => {
              setShowCreate(false);
              load();
            }}
          />
        )}
      </main>
    </>
  );
}
