"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface UseSWROptions {
  /** Time in ms before cached data is considered stale. Default: 30_000 (30s). */
  staleTime?: number;
  /** Auto-revalidate on window focus. Default: true. */
  revalidateOnFocus?: boolean;
}

interface UseSWRReturn<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** True when showing stale data and revalidating in the background. */
  isValidating: boolean;
  /** Force a revalidation. */
  mutate: () => void;
}

// Simple in-memory cache keyed by string
const cache = new Map<string, { data: unknown; timestamp: number }>();

/**
 * Stale-while-revalidate data fetching hook.
 *
 * Returns cached data instantly (if available and within staleTime),
 * then revalidates in the background. New data triggers a re-render.
 */
export function useSWR<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: UseSWROptions = {},
): UseSWRReturn<T> {
  const { staleTime = 30_000, revalidateOnFocus = true } = options;

  const [data, setData] = useState<T | null>(() => {
    const entry = cache.get(key);
    return entry ? (entry.data as T) : null;
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!cache.has(key));
  const [isValidating, setIsValidating] = useState(false);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const keyRef = useRef(key);
  keyRef.current = key;

  const revalidate = useCallback(async () => {
    const currentKey = keyRef.current;
    setIsValidating(true);
    try {
      const result = await fetcherRef.current();
      cache.set(currentKey, { data: result, timestamp: Date.now() });
      setData(result);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fetch failed");
    } finally {
      setIsValidating(false);
      setLoading(false);
    }
  }, []);

  // Initial fetch or revalidation if stale
  useEffect(() => {
    const entry = cache.get(key);
    if (entry) {
      setData(entry.data as T);
      const isStale = Date.now() - entry.timestamp > staleTime;
      if (isStale) {
        revalidate();
      } else {
        setLoading(false);
      }
    } else {
      revalidate();
    }
  }, [key, staleTime, revalidate]);

  // Revalidate on window focus
  useEffect(() => {
    if (!revalidateOnFocus) return;
    const onFocus = () => {
      const entry = cache.get(keyRef.current);
      if (!entry || Date.now() - entry.timestamp > staleTime) {
        revalidate();
      }
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [revalidateOnFocus, staleTime, revalidate]);

  return { data, error, loading, isValidating, mutate: revalidate };
}
