import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { usePolling } from "@/lib/hooks/usePolling";

describe("usePolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Ensure document.hidden is false
    Object.defineProperty(document, "hidden", { value: false, configurable: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("calls fn on the specified interval when enabled", () => {
    const fn = vi.fn();
    renderHook(() => usePolling({ fn, intervalMs: 1000, enabled: true }));

    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1000);
    expect(fn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(1000);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("does not call fn when disabled", () => {
    const fn = vi.fn();
    renderHook(() => usePolling({ fn, intervalMs: 500, enabled: false }));

    vi.advanceTimersByTime(2000);
    expect(fn).not.toHaveBeenCalled();
  });

  it("skips calls when document is hidden", () => {
    const fn = vi.fn();
    renderHook(() =>
      usePolling({ fn, intervalMs: 500, enabled: true, skipWhenHidden: true }),
    );

    // Tab visible — should fire
    vi.advanceTimersByTime(500);
    expect(fn).toHaveBeenCalledTimes(1);

    // Tab hidden — should skip
    Object.defineProperty(document, "hidden", { value: true, configurable: true });
    vi.advanceTimersByTime(500);
    expect(fn).toHaveBeenCalledTimes(1); // Still 1, not 2

    // Tab visible again — should fire
    Object.defineProperty(document, "hidden", { value: false, configurable: true });
    vi.advanceTimersByTime(500);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("cleans up interval on unmount", () => {
    const fn = vi.fn();
    const { unmount } = renderHook(() =>
      usePolling({ fn, intervalMs: 500, enabled: true }),
    );

    vi.advanceTimersByTime(500);
    expect(fn).toHaveBeenCalledTimes(1);

    unmount();

    vi.advanceTimersByTime(2000);
    expect(fn).toHaveBeenCalledTimes(1); // No more calls after unmount
  });
});
