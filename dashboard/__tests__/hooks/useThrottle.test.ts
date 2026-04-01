import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useThrottle } from "@/lib/hooks/useThrottle";

describe("useThrottle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fires immediately on first call", () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useThrottle(fn, 1000));

    act(() => {
      result.current();
    });

    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("throttles rapid calls to one per limit", () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useThrottle(fn, 500));

    act(() => {
      result.current(); // fires immediately
      result.current(); // throttled
      result.current(); // throttled (replaces previous trailing)
    });

    expect(fn).toHaveBeenCalledTimes(1);

    // Advance past the throttle window — trailing call fires
    act(() => {
      vi.advanceTimersByTime(600);
    });

    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("allows calls after the throttle window expires", () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useThrottle(fn, 200));

    act(() => {
      result.current(); // fires
    });
    expect(fn).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(300);
      result.current(); // fires (window expired)
    });
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("does not fire trailing call if no extra calls were made", () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useThrottle(fn, 500));

    act(() => {
      result.current(); // fires immediately
    });

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // Only the initial call, no trailing
    expect(fn).toHaveBeenCalledTimes(1);
  });
});
