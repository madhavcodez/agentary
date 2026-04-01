"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  startMission,
  stopMission,
  rerunMission,
  synthesizeMissionReport,
} from "@/lib/api";

interface UseMissionActionsOptions {
  missionId: string;
  /** Called after a successful action to refresh data. */
  onRefresh: () => void;
  /** Called when an action fails. */
  onError: (message: string) => void;
}

interface UseMissionActionsReturn {
  actionLoading: boolean;
  synthesizing: boolean;
  synthesizeSuccess: boolean;
  handleStart: () => Promise<void>;
  handleStop: () => Promise<void>;
  handleRerun: () => Promise<void>;
  handleSynthesize: () => Promise<void>;
}

/**
 * Encapsulates mission action handlers (start, stop, rerun, synthesize).
 * Manages loading states and error handling for each action.
 */
export function useMissionActions({
  missionId,
  onRefresh,
  onError,
}: UseMissionActionsOptions): UseMissionActionsReturn {
  const router = useRouter();
  const [actionLoading, setActionLoading] = useState(false);
  const [synthesizing, setSynthesizing] = useState(false);
  const [synthesizeSuccess, setSynthesizeSuccess] = useState(false);

  const handleStart = useCallback(async () => {
    setActionLoading(true);
    try {
      await startMission(missionId);
      onRefresh();
    } catch (e: unknown) {
      onError(e instanceof Error ? e.message : "Failed to start");
    } finally {
      setActionLoading(false);
    }
  }, [missionId, onRefresh, onError]);

  const handleStop = useCallback(async () => {
    setActionLoading(true);
    try {
      await stopMission(missionId);
      onRefresh();
    } catch (e: unknown) {
      onError(e instanceof Error ? e.message : "Failed to stop");
    } finally {
      setActionLoading(false);
    }
  }, [missionId, onRefresh, onError]);

  const handleRerun = useCallback(async () => {
    setActionLoading(true);
    try {
      await rerunMission(missionId);
      onRefresh();
    } catch (e: unknown) {
      onError(e instanceof Error ? e.message : "Failed to rerun");
    } finally {
      setActionLoading(false);
    }
  }, [missionId, onRefresh, onError]);

  const handleSynthesize = useCallback(async () => {
    setSynthesizing(true);
    setSynthesizeSuccess(false);
    try {
      const result = await synthesizeMissionReport(missionId);
      setSynthesizeSuccess(true);
      setTimeout(() => {
        router.push(`/reports/${result.report.id}`);
      }, 800);
    } catch (e: unknown) {
      onError(e instanceof Error ? e.message : "Failed to synthesize report");
    } finally {
      setSynthesizing(false);
    }
  }, [missionId, onError, router]);

  return {
    actionLoading,
    synthesizing,
    synthesizeSuccess,
    handleStart,
    handleStop,
    handleRerun,
    handleSynthesize,
  };
}
