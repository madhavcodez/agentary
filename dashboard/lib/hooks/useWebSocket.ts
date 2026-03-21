"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "@/lib/auth";
import type { LiveEvent } from "@/lib/types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const MAX_EVENTS = 200;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const HEARTBEAT_MS = 30000;

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface UseWebSocketReturn {
  events: LiveEvent[];
  status: ConnectionStatus;
  subscribe: (projectId: string) => void;
  clearEvents: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const clearEvents = useCallback(() => setEvents([]), []);

  const addEvent = useCallback((event: LiveEvent) => {
    setEvents((prev) => {
      const next = [...prev, event];
      return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
    });
  }, []);

  const subscribe = useCallback((projectId: string) => {
    wsRef.current?.send(JSON.stringify({ type: "subscribe", project_id: projectId }));
  }, []);

  const connect = useCallback(() => {
    const token = getToken();
    if (!token) {
      setStatus("error");
      return;
    }

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus("connecting");
    const ws = new WebSocket(`${WS_BASE}/ws/live-feed?token=${encodeURIComponent(token)}`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setStatus("connected");
      retriesRef.current = 0;

      // Start heartbeat
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, HEARTBEAT_MS);
    };

    ws.onmessage = (e) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(e.data as string) as LiveEvent;
        if (data.event_type && data.event_type !== "pong") {
          addEvent(data);
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
      setStatus("error");
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
      setStatus("disconnected");

      // Auto-reconnect with exponential backoff
      const delay = Math.min(
        RECONNECT_BASE_MS * Math.pow(2, retriesRef.current),
        RECONNECT_MAX_MS,
      );
      retriesRef.current += 1;
      setTimeout(() => {
        if (mountedRef.current) connect();
      }, delay);
    };
  }, [addEvent]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { events, status, subscribe, clearEvents };
}
