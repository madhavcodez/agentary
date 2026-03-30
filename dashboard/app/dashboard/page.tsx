"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchRecentEvents,
  fetchMonitors,
  fetchMissions,
  fetchFindings,
  fetchUnreadAlertCount,
} from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { useWS } from "@/components/WebSocketProvider";
import type { WSEvent } from "@/lib/types/events";
import type { MonitorSummary, LiveEvent } from "@/lib/types";
import StatsBar from "@/components/dashboard/StatsBar";
import ActiveMissions from "@/components/dashboard/ActiveMissions";
import LiveActivityFeed from "@/components/dashboard/LiveActivityFeed";
import MonitorsPanel from "@/components/dashboard/MonitorsPanel";

const MAX_FEED_EVENTS = 200;

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
  const { toast } = useToast();
  const { connectionState, subscribe } = useWS();
  const hasShownError = useRef(false);
  const disconnectedSinceRef = useRef<number | null>(null);

  const loadData = useCallback(async () => {
    const results = await Promise.allSettled([
      fetchRecentEvents(20),
      fetchMonitors(),
      fetchMissions(),
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
      missionList = (results[2].value as typeof missionList).filter((m) =>
        ["queued", "running"].includes(m.status),
      );
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

    const failedCount = results.filter((r) => r.status === "rejected").length;
    if (failedCount > 0 && !hasShownError.current) {
      toast("Some dashboard data failed to load", "error");
      hasShownError.current = true;
    }

    setStatsData({
      activeMissions: missionList.length,
      totalFindings: findingsCount,
      activeMonitors: monitorList.filter((m) => m.status === "active").length,
      unreadAlerts: unread,
      connectedClients: 1,
    });

    setLoading(false);
  }, [toast]);

  // Initial REST fetch
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Re-fetch full state on WS reconnect
  useEffect(() => {
    if (connectionState === "connected") {
      disconnectedSinceRef.current = null;
      loadData();
    } else if (connectionState === "disconnected") {
      if (disconnectedSinceRef.current === null) {
        disconnectedSinceRef.current = Date.now();
      }
    }
  }, [connectionState, loadData]);

  // Subscribe to real-time events via WebSocket
  useEffect(() => {
    const handleEvent = (wsEvent: WSEvent) => {
      // Append to live feed as a LiveEvent
      const liveEvent: LiveEvent = {
        event_id: wsEvent.correlation_id ?? `ws-${Date.now()}`,
        event_type: wsEvent.event_type,
        scope: wsEvent.project_id ? "project" : wsEvent.user_id ? "user" : "global",
        user_id: wsEvent.user_id ?? null,
        project_id: wsEvent.project_id ?? null,
        data: wsEvent.data,
        timestamp: new Date(wsEvent.timestamp).getTime() / 1000,
      };
      setEvents((prev) => {
        const next = [...prev, liveEvent];
        return next.length > MAX_FEED_EVENTS ? next.slice(-MAX_FEED_EVENTS) : next;
      });

      // Mission state changes: refresh missions + stats
      if (wsEvent.event_type.startsWith("mission.")) {
        loadData();
      }

      // Monitor events: refresh monitors
      if (wsEvent.event_type.startsWith("monitor.")) {
        loadData();
      }

      // Finding events: refresh stats
      if (wsEvent.event_type === "finding.created") {
        loadData();
      }
    };

    const unsub = subscribe("*", handleEvent);
    return unsub;
  }, [subscribe, loadData]);

  // Fallback: poll if WS disconnected for >5s
  useEffect(() => {
    if (connectionState !== "disconnected") return;

    const interval = setInterval(() => {
      if (
        disconnectedSinceRef.current !== null &&
        Date.now() - disconnectedSinceRef.current > 5000 &&
        !document.hidden
      ) {
        loadData();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [connectionState, loadData]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <div className="text-center py-20 text-gray-500 text-sm">Loading command center...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 space-y-6">
      <h1 className="text-3xl font-bold text-gray-100 tracking-tight">Dashboard</h1>

      {/* Stats Bar — full width */}
      <StatsBar
        activeMissions={statsData.activeMissions}
        totalFindings={statsData.totalFindings}
        activeMonitors={statsData.activeMonitors}
        unreadAlerts={statsData.unreadAlerts}
        connectedClients={statsData.connectedClients}
      />

      {/* 2-column grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
