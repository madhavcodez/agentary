"use client";

import { useState, useCallback, useRef } from "react";

interface UseOptimisticReturn<T> {
  /** Current value (optimistic or confirmed). */
  value: T;
  /** True while the API call is in flight. */
  pending: boolean;
  /** Apply an optimistic update, execute the async action, then confirm or rollback. */
  update: (optimisticValue: T, action: () => Promise<T>) => Promise<void>;
}

/**
 * Manages optimistic UI updates.
 *
 * Immediately sets the value to `optimisticValue`, runs the async `action`,
 * then either confirms with the real result or rolls back to the previous value.
 */
export function useOptimistic<T>(initialValue: T): UseOptimisticReturn<T> {
  const [value, setValue] = useState<T>(initialValue);
  const [pending, setPending] = useState(false);
  const previousRef = useRef<T>(initialValue);

  const update = useCallback(
    async (optimisticValue: T, action: () => Promise<T>) => {
      previousRef.current = value;
      setValue(optimisticValue);
      setPending(true);

      try {
        const confirmed = await action();
        setValue(confirmed);
      } catch {
        // Rollback on failure
        setValue(previousRef.current);
      } finally {
        setPending(false);
      }
    },
    [value],
  );

  return { value, pending, update };
}
