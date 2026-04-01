"use client";

import { useEffect, useRef, useState } from "react";
import { usePolling } from "@/lib/hooks/usePolling";
import { useBatchedUpdates } from "@/lib/hooks/useBatchedUpdates";
import { useThrottle } from "@/lib/hooks/useThrottle";
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
import ActiveMissions from "@/components/dashboard/ActiveMissions";
import LiveActivityFeed from "@/components/dashboard/LiveActivityFeed";
import MonitorsPanel from "@/components/dashboard/MonitorsPanel";
import GlassCard from "@/components/ui/GlassCard";
import { useAsync } from "@/lib/hooks/useAsync";
import { DashboardSkeleton } from "@/components/ui/Skeleton";

const MAX_FEED_EVENTS = 200;

interface DashboardData {
  events: LiveEvent[];
  monitors: MonitorSummary[];
  activeMissions: Array<{ id: string; title: string; status: string; project_id: string | null; created_at: string | null }>;
  stats: {
    activeMissions: number;
    totalFindings: number;
    activeMonitors: number;
    unreadAlerts: number;
  };
  hadPartialFailure: boolean;
}

export default function DashboardPage() {
  const { toast } = useToast();
  const { connectionState, subscribe } = useWS();
  const hasShownError = useRef(false);
  const disconnectedSinceRef = useRef<number | null>(null);

  // Live events (augmented by WS in real time)
  const [liveEvents, setLiveEvents] = useState<LiveEvent[]>([]);

  const { data, loading, retry } = useAsync<DashboardData>(async () => {
    const results = await Promise.allSettled([
      fetchRecentEvents(20),
      fetchMonitors(),
      fetchMissions(),
      fetchFindings({ limit: 100 }),
      fetchUnreadAlertCount(),
    ]);

    // Events
    const events: LiveEvent[] =
      results[0].status === "fulfilled" ? (results[0].value as unknown as LiveEvent[]) : [];

    // Monitors
    const monitorList: MonitorSummary[] =
      results[1].status === "fulfilled" ? (results[1].value as MonitorSummary[]) : [];

    // Active missions
    type RawMission = { id: string; name: string; status: string; project_id: string; created_at: string };
    const rawMissions: RawMission[] =
      results[2].status === "fulfilled"
        ? (results[2].value as RawMission[]).filter((m) =>
            ["queued", "running"].includes(m.status),
          )
        : [];
    const activeMissions = rawMissions.map((m) => ({
      id: m.id,
      title: m.name,
      status: m.status,
      project_id: m.project_id as string | null,
      created_at: m.created_at as string | null,
    }));

    // Stats
    const findingsCount =
      results[3].status === "fulfilled" ? (results[3].value as unknown[]).length : 0;
    const unread =
      results[4].status === "fulfilled" ? (results[4].value as { unread: number }).unread : 0;

    const hadPartialFailure = results.some((r) => r.status === "rejected");

    return {
      events,
      monitors: monitorList,
      activeMissions,
      stats: {
        activeMissions: rawMissions.length,
        totalFindings: findingsCount,
        activeMonitors: monitorList.filter((m) => m.status === "active").length,
        unreadAlerts: unread,
      },
      hadPartialFailure,
    };
  }, []);

  // Show toast on partial failure (once)
  useEffect(() => {
    if (data?.hadPartialFailure && !hasShownError.current) {
      toast("Some dashboard data failed to load", "error");
      hasShownError.current = true;
    }
  }, [data, toast]);

  // Seed live events from initial fetch
  useEffect(() => {
    if (data?.events) {
      setLiveEvents(data.events);
    }
  }, [data?.events]);

  // Re-fetch full state on WS reconnect
  useEffect(() => {
    if (connectionState === "connected") {
      disconnectedSinceRef.current = null;
      retry();
    } else if (connectionState === "disconnected") {
      if (disconnectedSinceRef.current === null) {
        disconnectedSinceRef.current = Date.now();
      }
    }
  }, [connectionState, retry]);

  // Throttle data refreshes to max 1 per 2s (prevents hammering API during active research)
  const throttledRetry = useThrottle(retry, 2000);

  // Batch rapid WS events into single state updates (reduces re-renders)
  const batchEvent = useBatchedUpdates<LiveEvent>((batch) => {
    setLiveEvents((prev) => {
      const next = [...prev, ...batch];
      return next.length > MAX_FEED_EVENTS ? next.slice(-MAX_FEED_EVENTS) : next;
    });
    // If any event in the batch requires a data refresh, do it once (throttled)
    if (batch.some((e) =>
      e.event_type.startsWith("mission.") ||
      e.event_type.startsWith("monitor.") ||
      e.event_type === "finding.created"
    )) {
      throttledRetry();
    }
  }, 100);

  // Subscribe to real-time events via WebSocket
  useEffect(() => {
    const handleEvent = (wsEvent: WSEvent) => {
      const liveEvent: LiveEvent = {
        event_id: wsEvent.correlation_id ?? `ws-${Date.now()}`,
        event_type: wsEvent.event_type,
        scope: wsEvent.project_id ? "project" : wsEvent.user_id ? "user" : "global",
        user_id: wsEvent.user_id ?? null,
        project_id: wsEvent.project_id ?? null,
        data: wsEvent.data,
        timestamp: new Date(wsEvent.timestamp).getTime() / 1000,
      };
      batchEvent(liveEvent);
    };

    const unsub = subscribe("*", handleEvent);
    return unsub;
  }, [subscribe, batchEvent]);

  // Fallback: poll if WS disconnected for >5s
  usePolling({
    fn: retry,
    intervalMs: 30000,
    enabled: connectionState === "disconnected" &&
      disconnectedSinceRef.current !== null &&
      Date.now() - (disconnectedSinceRef.current ?? 0) > 5000,
  });

  if (loading) {
    return <DashboardSkeleton />;
  }

  const connectionDot =
    connectionState === "connected"
      ? "bg-emerald-400"
      : connectionState === "connecting" || connectionState === "reconnecting"
        ? "bg-amber-400 animate-pulse"
        : "bg-red-400";

  const monitors = data?.monitors ?? [];
  const activeMissions = data?.activeMissions ?? [];
  const statsData = data?.stats ?? { activeMissions: 0, totalFindings: 0, activeMonitors: 0, unreadAlerts: 0 };

  return (
    <div className="max-w-5xl mx-auto px-6 py-6 space-y-5">
      {/* Compact header */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-gray-200 tracking-tight">
          System Dashboard
        </h1>
        <span className={`w-2 h-2 rounded-full ${connectionDot}`} />
      </div>

      {/* Compact activity log */}
      <GlassCard className="rounded-xl p-4 max-h-[220px] overflow-y-auto">
        <LiveActivityFeed events={liveEvents.slice(-10)} />
      </GlassCard>

      {/* 2-column grid: Missions | Monitors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GlassCard className="rounded-xl p-4">
          <ActiveMissions missions={activeMissions} runs={[]} />
        </GlassCard>
        <GlassCard className="rounded-xl p-4">
          <MonitorsPanel monitors={monitors} />
        </GlassCard>
      </div>

      {/* Findings summary stat line */}
      <GlassCard className="rounded-xl px-4 py-3 flex items-center justify-between text-sm">
        <span className="text-gray-400">Active Findings</span>
        <div className="flex items-center gap-4">
          <span className="text-gray-100 font-semibold">{statsData.totalFindings}</span>
          {statsData.unreadAlerts > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300">
              {statsData.unreadAlerts} unread alert{statsData.unreadAlerts !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </GlassCard>
    </div>
  );
}
