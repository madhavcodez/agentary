"use client";

import { useCallback, useRef } from "react";

/**
 * Batches rapid-fire calls into a single flush after a debounce window.
 *
 * Useful for WebSocket events: instead of updating state per-event
 * (causing N re-renders), we collect events and flush them all at once.
 *
 * @param flush - Called with all accumulated items when the batch window closes.
 * @param windowMs - Debounce window in milliseconds (default: 50ms).
 */
export function useBatchedUpdates<T>(
  flush: (items: T[]) => void,
  windowMs: number = 50,
): (item: T) => void {
  const bufferRef = useRef<T[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flushRef = useRef(flush);
  flushRef.current = flush;

  return useCallback(
    (item: T) => {
      bufferRef.current.push(item);

      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      timerRef.current = setTimeout(() => {
        const batch = bufferRef.current;
        bufferRef.current = [];
        timerRef.current = null;
        if (batch.length > 0) {
          flushRef.current(batch);
        }
      }, windowMs);
    },
    [windowMs],
  );
}
