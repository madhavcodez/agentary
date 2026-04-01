"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "@/lib/auth";
import type { WSEvent } from "@/lib/types/events";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const HEARTBEAT_MS = 30000;

export type ConnectionState =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting";

type EventHandler = (event: WSEvent) => void;

interface UseWebSocketOptions {
  projectId?: string;
  onEvent?: EventHandler;
  enabled?: boolean;
}

export interface UseWebSocketReturn {
  connectionState: ConnectionState;
  subscribe: (eventType: string, handler: EventHandler) => () => void;
}

export function useWebSocket(
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const { projectId, onEvent, enabled = true } = options;

  const [connectionState, setConnectionState] =
    useState<ConnectionState>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map());
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const subscribe = useCallback(
    (eventType: string, handler: EventHandler): (() => void) => {
      if (!handlersRef.current.has(eventType)) {
        handlersRef.current.set(eventType, new Set());
      }
      handlersRef.current.get(eventType)!.add(handler);
      return () => {
        handlersRef.current.get(eventType)?.delete(handler);
      };
    },
    [],
  );

  const connect = useCallback(() => {
    if (!enabled) return;
    const token = getToken() ?? "";

    // Clean up existing connection
    if (wsRef.current) {
      try { wsRef.current.close(); } catch { /* ignore */ }
      wsRef.current = null;
    }
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }

    setConnectionState("connecting");

    const url = projectId
      ? `${WS_BASE}/api/live-feed/${projectId}?token=${encodeURIComponent(token)}`
      : `${WS_BASE}/ws/live-feed?token=${encodeURIComponent(token)}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      // WebSocket constructor can throw if URL is invalid
      setConnectionState("disconnected");
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnectionState("connected");
      reconnectAttemptRef.current = 0;

      // Start heartbeat
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, HEARTBEAT_MS);
    };

    ws.onmessage = (msgEvent) => {
      if (!mountedRef.current) return;
      try {
        const event: WSEvent = JSON.parse(msgEvent.data as string);
        if (!event.event_type || event.event_type === "pong") return;

        // Call global onEvent handler
        onEventRef.current?.(event);

        // Call type-specific handlers
        const handlers = handlersRef.current.get(event.event_type);
        if (handlers) {
          handlers.forEach((handler) => handler(event));
        }

        // Call wildcard handlers
        const wildcardHandlers = handlersRef.current.get("*");
        if (wildcardHandlers) {
          wildcardHandlers.forEach((handler) => handler(event));
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
      ws.close();
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;

      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }

      wsRef.current = null;
      setConnectionState("disconnected");

      // Auto-reconnect with exponential backoff — only if we have a token
      const hasToken = !!getToken();
      if (
        enabled &&
        hasToken &&
        reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS
      ) {
        const delay = Math.min(
          RECONNECT_BASE_MS * Math.pow(2, reconnectAttemptRef.current),
          RECONNECT_MAX_MS,
        );
        reconnectAttemptRef.current++;
        setConnectionState("reconnecting");
        setTimeout(() => {
          if (mountedRef.current) connect();
        }, delay);
      }
    };
  }, [enabled, projectId]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { connectionState, subscribe };
}
