import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOptimistic } from "@/lib/hooks/useOptimistic";

describe("useOptimistic", () => {
  it("starts with initial value", () => {
    const { result } = renderHook(() => useOptimistic("draft"));
    expect(result.current.value).toBe("draft");
    expect(result.current.pending).toBe(false);
  });

  it("confirms with action result after resolving", async () => {
    const action = vi.fn().mockResolvedValue("confirmed");
    const { result } = renderHook(() => useOptimistic("draft"));

    await act(async () => {
      await result.current.update("running", action);
    });

    // After action resolves, value should be the confirmed result
    expect(result.current.value).toBe("confirmed");
    expect(result.current.pending).toBe(false);
    expect(action).toHaveBeenCalledTimes(1);
  });

  it("rolls back on action failure", async () => {
    const action = vi.fn().mockRejectedValue(new Error("fail"));
    const { result } = renderHook(() => useOptimistic("original"));

    await act(async () => {
      await result.current.update("optimistic", action);
    });

    // Should roll back to the value before update was called
    expect(result.current.value).toBe("original");
    expect(result.current.pending).toBe(false);
  });

  it("calls the action function", async () => {
    const action = vi.fn().mockResolvedValue("done");
    const { result } = renderHook(() => useOptimistic("start"));

    await act(async () => {
      await result.current.update("pending", action);
    });

    expect(action).toHaveBeenCalledTimes(1);
  });
});
