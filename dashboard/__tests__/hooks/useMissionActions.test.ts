import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useMissionActions } from "@/lib/hooks/useMissionActions";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock API functions
const mockStartMission = vi.fn();
const mockStopMission = vi.fn();
const mockRerunMission = vi.fn();
const mockSynthesizeMissionReport = vi.fn();

vi.mock("@/lib/api", () => ({
  startMission: (...args: unknown[]) => mockStartMission(...args),
  stopMission: (...args: unknown[]) => mockStopMission(...args),
  rerunMission: (...args: unknown[]) => mockRerunMission(...args),
  synthesizeMissionReport: (...args: unknown[]) => mockSynthesizeMissionReport(...args),
}));

describe("useMissionActions", () => {
  const onRefresh = vi.fn();
  const onError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockStartMission.mockResolvedValue({});
    mockStopMission.mockResolvedValue({});
    mockRerunMission.mockResolvedValue({});
    mockSynthesizeMissionReport.mockResolvedValue({ report: { id: "r1" } });
  });

  it("starts with no loading states", () => {
    const { result } = renderHook(() =>
      useMissionActions({ missionId: "m1", onRefresh, onError }),
    );
    expect(result.current.actionLoading).toBe(false);
    expect(result.current.synthesizing).toBe(false);
    expect(result.current.synthesizeSuccess).toBe(false);
  });

  it("handleStart calls API and refreshes", async () => {
    const { result } = renderHook(() =>
      useMissionActions({ missionId: "m1", onRefresh, onError }),
    );

    await act(async () => {
      await result.current.handleStart();
    });

    expect(mockStartMission).toHaveBeenCalledWith("m1");
    expect(onRefresh).toHaveBeenCalled();
    expect(result.current.actionLoading).toBe(false);
  });

  it("handleStop calls API and refreshes", async () => {
    const { result } = renderHook(() =>
      useMissionActions({ missionId: "m1", onRefresh, onError }),
    );

    await act(async () => {
      await result.current.handleStop();
    });

    expect(mockStopMission).toHaveBeenCalledWith("m1");
    expect(onRefresh).toHaveBeenCalled();
  });

  it("handleRerun calls API and refreshes", async () => {
    const { result } = renderHook(() =>
      useMissionActions({ missionId: "m1", onRefresh, onError }),
    );

    await act(async () => {
      await result.current.handleRerun();
    });

    expect(mockRerunMission).toHaveBeenCalledWith("m1");
    expect(onRefresh).toHaveBeenCalled();
  });

  it("handleStart reports error on failure", async () => {
    mockStartMission.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() =>
      useMissionActions({ missionId: "m1", onRefresh, onError }),
    );

    await act(async () => {
      await result.current.handleStart();
    });

    expect(onError).toHaveBeenCalledWith("Network error");
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("handleSynthesize sets success and navigates", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() =>
      useMissionActions({ missionId: "m1", onRefresh, onError }),
    );

    await act(async () => {
      await result.current.handleSynthesize();
    });

    expect(mockSynthesizeMissionReport).toHaveBeenCalledWith("m1");
    expect(result.current.synthesizeSuccess).toBe(true);

    // Navigate after timeout
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(mockPush).toHaveBeenCalledWith("/reports/r1");
    vi.useRealTimers();
  });
});
