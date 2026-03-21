"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchRecentEvents,
  fetchMonitors,
  fetchMissions,
  fetchFindings,
  fetchUnreadAlertCount,
} from "@/lib/api";
import type { MonitorSummary, LiveEvent } from "@/lib/types";
import StatsBar from "@/components/dashboard/StatsBar";
import ActiveMissions from "@/components/dashboard/ActiveMissions";
import LiveActivityFeed from "@/components/dashboard/LiveActivityFeed";
import MonitorsPanel from "@/components/dashboard/MonitorsPanel";

export default function DashboardPage() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [monitors, setMonitors] = useState<MonitorSummary[]>([]);
  const [activeMissions, setActiveMissions] = useState<
    Array<{ id: string; title: string; status: string; project_id: string | null; created_at: string | null }>
  >([]);
  const [statsData, setStatsData] = useState({
    activeMissions: 0,
    totalFindings: 0,
    activeMonitors: 0,
    unreadAlerts: 0,
    connectedClients: 0,
  });
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    const results = await Promise.allSettled([
      fetchRecentEvents(20),
      fetchMonitors(),
      fetchMissions({ status: "active" }),
      fetchFindings({ limit: 100 }),
      fetchUnreadAlertCount(),
    ]);

    // Events
    if (results[0].status === "fulfilled") {
      setEvents(results[0].value as unknown as LiveEvent[]);
    }

    // Monitors
    let monitorList: MonitorSummary[] = [];
    if (results[1].status === "fulfilled") {
      monitorList = results[1].value as MonitorSummary[];
      setMonitors(monitorList);
    }

    // Active missions
    let missionList: Array<{ id: string; name: string; status: string; project_id: string; created_at: string }> = [];
    if (results[2].status === "fulfilled") {
      missionList = results[2].value as typeof missionList;
      setActiveMissions(
        missionList.map((m) => ({
          id: m.id,
          title: m.name,
          status: m.status,
          project_id: m.project_id,
          created_at: m.created_at,
        })),
      );
    }

    // Stats
    let findingsCount = 0;
    if (results[3].status === "fulfilled") {
      findingsCount = (results[3].value as unknown[]).length;
    }

    let unread = 0;
    if (results[4].status === "fulfilled") {
      unread = (results[4].value as { unread: number }).unread;
    }

    setStatsData({
      activeMissions: missionList.length,
      totalFindings: findingsCount,
      activeMonitors: monitorList.filter((m) => m.status === "active").length,
      unreadAlerts: unread,
      connectedClients: 1,
    });

    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <div className="text-center py-20 text-gray-500 text-sm">Loading command center...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Command Center</h1>

      {/* Stats Bar — full width */}
      <StatsBar
        activeMissions={statsData.activeMissions}
        totalFindings={statsData.totalFindings}
        activeMonitors={statsData.activeMonitors}
        unreadAlerts={statsData.unreadAlerts}
        connectedClients={statsData.connectedClients}
      />

      {/* 2-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — wider */}
        <div className="lg:col-span-2">
          <LiveActivityFeed events={events} />
        </div>

        {/* Right column — stacked */}
        <div className="space-y-6">
          <ActiveMissions missions={activeMissions} runs={[]} />
          <MonitorsPanel monitors={monitors} />
        </div>
      </div>
    </div>
  );
}
