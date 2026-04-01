"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface UseHealthCheckOptions {
  /** Health endpoint URL. */
  url?: string;
  /** Check interval in ms. Default: 15_000 (15s). */
  intervalMs?: number;
  /** Only poll when this is true. Default: true. */
  enabled?: boolean;
}

interface UseHealthCheckReturn {
  /** True when the backend health check passes. */
  healthy: boolean;
  /** Timestamp of last successful check, or null. */
  lastCheckedAt: number | null;
  /** Force an immediate health check. */
  check: () => Promise<boolean>;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Polls the backend health endpoint on an interval.
 * Useful for detecting when the backend recovers after downtime
 * so the UI can auto-reconnect WebSockets and refresh data.
 */
export function useHealthCheck(options: UseHealthCheckOptions = {}): UseHealthCheckReturn {
  const {
    url = `${BASE_URL}/health`,
    intervalMs = 15_000,
    enabled = true,
  } = options;

  const [healthy, setHealthy] = useState(true);
  const [lastCheckedAt, setLastCheckedAt] = useState<number | null>(null);
  const urlRef = useRef(url);
  urlRef.current = url;

  const check = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(urlRef.current, {
        method: "GET",
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      });
      const ok = res.ok;
      setHealthy(ok);
      if (ok) setLastCheckedAt(Date.now());
      return ok;
    } catch {
      setHealthy(false);
      return false;
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    // Initial check
    check();

    const id = setInterval(() => {
      if (!document.hidden) check();
    }, intervalMs);

    return () => clearInterval(id);
  }, [enabled, intervalMs, check]);

  return { healthy, lastCheckedAt, check };
}
