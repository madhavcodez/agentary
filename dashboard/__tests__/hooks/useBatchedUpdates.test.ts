import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useBatchedUpdates } from "@/lib/hooks/useBatchedUpdates";

describe("useBatchedUpdates", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("batches multiple rapid calls into a single flush", () => {
    const flush = vi.fn();
    const { result } = renderHook(() => useBatchedUpdates<number>(flush, 50));

    act(() => {
      result.current(1);
      result.current(2);
      result.current(3);
    });

    // Not flushed yet
    expect(flush).not.toHaveBeenCalled();

    // Advance past the window
    act(() => {
      vi.advanceTimersByTime(60);
    });

    expect(flush).toHaveBeenCalledTimes(1);
    expect(flush).toHaveBeenCalledWith([1, 2, 3]);
  });

  it("resets the timer on each new item", () => {
    const flush = vi.fn();
    const { result } = renderHook(() => useBatchedUpdates<string>(flush, 100));

    act(() => {
      result.current("a");
    });

    // 80ms later, add another item — should reset the 100ms window
    act(() => {
      vi.advanceTimersByTime(80);
      result.current("b");
    });

    // At 160ms from start (80ms after "b"), not yet flushed
    act(() => {
      vi.advanceTimersByTime(80);
    });
    expect(flush).not.toHaveBeenCalled();

    // At 200ms from start (100ms after "b"), should flush
    act(() => {
      vi.advanceTimersByTime(30);
    });
    expect(flush).toHaveBeenCalledWith(["a", "b"]);
  });

  it("does not flush if buffer is empty", () => {
    const flush = vi.fn();
    renderHook(() => useBatchedUpdates<number>(flush, 50));

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(flush).not.toHaveBeenCalled();
  });
});
