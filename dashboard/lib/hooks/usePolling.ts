"use client";

import { useEffect, useRef } from "react";

interface UsePollingOptions {
  /** Function to call on each poll interval. */
  fn: () => void;
  /** Interval in milliseconds. */
  intervalMs: number;
  /** Only poll when this is true. */
  enabled: boolean;
  /** Skip polling when the tab is hidden. */
  skipWhenHidden?: boolean;
}

/**
 * Calls `fn` on a recurring interval while `enabled` is true.
 * Automatically pauses when the browser tab is hidden (opt-in).
 */
export function usePolling({
  fn,
  intervalMs,
  enabled,
  skipWhenHidden = true,
}: UsePollingOptions): void {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!enabled) return;

    const tick = () => {
      if (skipWhenHidden && document.hidden) return;
      fnRef.current();
    };

    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs, skipWhenHidden]);
}
