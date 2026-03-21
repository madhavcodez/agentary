"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import StatsBar from "@/components/dashboard/StatsBar";
import ActiveMissions from "@/components/dashboard/ActiveMissions";
import LiveActivityFeed from "@/components/dashboard/LiveActivityFeed";
import MonitorsPanel from "@/components/dashboard/MonitorsPanel";
import AlertCenter from "@/components/dashboard/AlertCenter";
import { useWebSocket } from "@/lib/hooks/useWebSocket";
import { fetchActiveInfo, fetchMonitors, fetchUnreadAlertCount } from "@/lib/api";
import type { ActiveInfo, MonitorSummary } from "@/lib/types";

export default function DashboardPage() {
  const { events, status } = useWebSocket();
  const [activeInfo, setActiveInfo] = useState<ActiveInfo | null>(null);
  const [monitors, setMonitors] = useState<MonitorSummary[]>([]);
  const [unreadAlerts, setUnreadAlerts] = useState(0);

  const loadData = useCallback(async () => {
    try {
      const [info, mons, alertCount] = await Promise.all([
        fetchActiveInfo(),
        fetchMonitors({ status: "active" }),
        fetchUnreadAlertCount(),
      ]);
      setActiveInfo(info);
      setMonitors(mons);
      setUnreadAlerts(alertCount.unread);
    } catch {
      // silently fail on initial load
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Refresh data when alert events arrive
  useEffect(() => {
    const lastEvent = events[events.length - 1];
    if (lastEvent?.event_type === "alert.created" || lastEvent?.event_type === "monitor.alert") {
      loadData();
    }
  }, [events.length, loadData]);

  return (
    <>
      <Nav />
      <main className="ml-64 min-h-screen bg-gray-950 text-gray-100">
        {/* Header */}
        <header className="sticky top-0 z-40 bg-gray-950/80 backdrop-blur-sm border-b border-gray-800">
          <div className="px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold text-gray-100">Command Center</h1>
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    status === "connected"
                      ? "bg-emerald-400 animate-pulse"
                      : status === "connecting"
                        ? "bg-amber-400 animate-pulse"
                        : "bg-red-400"
                  }`}
                />
                <span className="text-xs text-gray-500">
                  {status === "connected"
                    ? "Live"
                    : status === "connecting"
                      ? "Connecting..."
                      : "Disconnected"}
                </span>
              </div>
            </div>
            <AlertCenter />
          </div>
        </header>

        <div className="px-6 py-6 space-y-6">
          {/* Stats Bar */}
          <StatsBar
            activeMissions={activeInfo?.active_missions.length ?? 0}
            totalFindings={events.filter((e) => e.event_type.includes("finding")).length}
            activeMonitors={monitors.length}
            unreadAlerts={unreadAlerts}
            connectedClients={activeInfo?.connected_clients ?? 0}
          />

          {/* Main Grid */}
          <div className="grid grid-cols-3 gap-6">
            {/* Left column: Active Missions */}
            <div className="space-y-6">
              <ActiveMissions
                missions={activeInfo?.active_missions ?? []}
                runs={activeInfo?.active_runs ?? []}
              />
              <MonitorsPanel monitors={monitors} />
            </div>

            {/* Center + Right: Live Feed (spans 2 columns) */}
            <div className="col-span-2">
              <LiveActivityFeed events={events} />
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
