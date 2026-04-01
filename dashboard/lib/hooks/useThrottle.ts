"use client";

import { useCallback, useRef } from "react";

/**
 * Returns a throttled version of the given function.
 * The function will be called at most once per `limitMs`.
 * Trailing calls are queued and fire after the cooldown.
 */
export function useThrottle<T extends (...args: never[]) => void>(
  fn: T,
  limitMs: number,
): T {
  const lastCallRef = useRef(0);
  const trailingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  return useCallback(
    ((...args: Parameters<T>) => {
      const now = Date.now();
      const elapsed = now - lastCallRef.current;

      if (elapsed >= limitMs) {
        lastCallRef.current = now;
        fnRef.current(...args);
      } else {
        // Schedule trailing call
        if (trailingRef.current) clearTimeout(trailingRef.current);
        trailingRef.current = setTimeout(() => {
          lastCallRef.current = Date.now();
          trailingRef.current = null;
          fnRef.current(...args);
        }, limitMs - elapsed);
      }
    }) as T,
    [limitMs],
  );
}
