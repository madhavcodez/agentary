"use client";

import { useEffect, useRef } from "react";

interface UseAutoReconnectOptions {
  /** Current backend health status. */
  healthy: boolean;
  /** Current WebSocket connection state. */
  connectionState: string;
  /** Called when the backend recovers and WS should reconnect. */
  onReconnect: () => void;
}

/**
 * Triggers a reconnection callback when the backend transitions
 * from unhealthy → healthy while the WebSocket is disconnected.
 *
 * This bridges the gap between the health check poller and
 * the WebSocket connection manager.
 */
export function useAutoReconnect({
  healthy,
  connectionState,
  onReconnect,
}: UseAutoReconnectOptions): void {
  const wasUnhealthyRef = useRef(false);
  const onReconnectRef = useRef(onReconnect);
  onReconnectRef.current = onReconnect;

  useEffect(() => {
    if (!healthy) {
      wasUnhealthyRef.current = true;
      return;
    }

    // Backend just recovered and WS is disconnected → reconnect
    if (wasUnhealthyRef.current && connectionState === "disconnected") {
      wasUnhealthyRef.current = false;
      onReconnectRef.current();
    }
  }, [healthy, connectionState]);
}
