"use client";

import { useCallback, useRef, useState } from "react";
import { getToken } from "@/lib/auth";
import type {
  ScoutJob,
  ScoutLogEntry,
  ScoutMode,
  ScoutPhaseState,
  ScoutStatus,
} from "@/lib/types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

let entryCounter = 0;

function logEntry(type: string, message: string, detail?: string): ScoutLogEntry {
  entryCounter += 1;
  return {
    id: `log-${entryCounter}-${Date.now()}`,
    timestamp: Date.now(),
    type,
    message,
    detail,
  };
}

const PHASE_LABELS: Record<string, string> = {
  ingest: "Ingesting Jobs",
  storing: "Storing Opportunities",
  filtering: "Filtering Candidates",
  scoring: "AI Scoring",
};

export interface ScoutState {
  phases: ScoutPhaseState[];
  liveJobs: ScoutJob[];
  status: ScoutStatus;
  progress: string;
  errorMessage: string;
  start: (mode: ScoutMode, skillsFilter: string[]) => void;
  pause: () => void;
  resume: () => void;
  cancel: () => void;
  reset: () => void;
}

export function useScoutWebSocket(): ScoutState {
  const [phases, setPhases] = useState<ScoutPhaseState[]>([]);
  const [liveJobs, setLiveJobs] = useState<ScoutJob[]>([]);
  const [status, setStatus] = useState<ScoutStatus>("idle");
  const [progress, setProgress] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const updatePhase = useCallback(
    (name: string, updater: (prev: ScoutPhaseState) => ScoutPhaseState) => {
      setPhases((prev) => {
        const idx = prev.findIndex((p) => p.name === name);
        if (idx === -1) {
          const newPhase: ScoutPhaseState = {
            name,
            label: PHASE_LABELS[name] ?? name,
            status: "pending",
            events: [],
          };
          return [...prev, updater(newPhase)];
        }
        const updated = [...prev];
        updated[idx] = updater(updated[idx]);
        return updated;
      });
    },
    [],
  );

  const addLogToPhase = useCallback(
    (phaseName: string, entry: ScoutLogEntry) => {
      updatePhase(phaseName, (p) => ({
        ...p,
        events: [...p.events, entry],
      }));
    },
    [updatePhase],
  );

  const start = useCallback(
    (mode: ScoutMode, skillsFilter: string[]) => {
      // Clean up any existing connection
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      setPhases([]);
      setLiveJobs([]);
      setProgress("");
      setErrorMessage("");
      entryCounter = 0;

      const ws = new WebSocket(`${WS_BASE}/scout/run`);
      wsRef.current = ws;

      ws.onopen = () => {
        const token = getToken();
        ws.send(
          JSON.stringify({
            token,
            mode,
            skills_filter: skillsFilter,
          }),
        );
        setStatus("running");
      };

      ws.onmessage = (e) => {
        let event: Record<string, unknown>;
        try {
          event = JSON.parse(e.data as string);
        } catch {
          return;
        }

        const type = event.type as string;

        switch (type) {
          case "phase": {
            const phase = event.phase as string;
            const phaseStatus = event.status as string;
            if (phaseStatus === "started") {
              updatePhase(phase, (p) => ({ ...p, status: "running" }));
              const detail = buildPhaseStartDetail(event);
              addLogToPhase(
                phase,
                logEntry("phase", `${PHASE_LABELS[phase] ?? phase} started`, detail),
              );
            } else if (phaseStatus === "done") {
              updatePhase(phase, (p) => ({ ...p, status: "done" }));
              const detail = buildPhaseDoneDetail(phase, event);
              addLogToPhase(
                phase,
                logEntry("phase", `${PHASE_LABELS[phase] ?? phase} complete`, detail),
              );
            }
            break;
          }

          case "source": {
            const source = event.source as string;
            const sourceStatus = event.status as string;
            if (sourceStatus === "fetching") {
              addLogToPhase(
                "ingest",
                logEntry("source", `Fetching from ${source}...`),
              );
            } else if (sourceStatus === "done") {
              addLogToPhase(
                "ingest",
                logEntry(
                  "source",
                  `${source}: ${event.jobs_found ?? 0} jobs found`,
                ),
              );
            } else if (sourceStatus === "error") {
              addLogToPhase(
                "ingest",
                logEntry("error", `${source} failed`, event.error as string),
              );
            }
            break;
          }

          case "progress": {
            const current = event.current as number;
            const total = event.total as number;
            setProgress(`Storing ${current} of ${total}...`);
            break;
          }

          case "filter": {
            const skill = event.skill as string;
            const matches = event.matches as number;
            addLogToPhase(
              "filtering",
              logEntry("filter", `${skill}: ${matches} matches`),
            );
            break;
          }

          case "filter_match": {
            const title = event.title as string;
            const company = event.company as string;
            const skillMatched = event.skill_matched as string;
            addLogToPhase(
              "filtering",
              logEntry(
                "filter_match",
                `${title} at ${company}`,
                `Matched: ${skillMatched}`,
              ),
            );
            break;
          }

          case "info": {
            const message = event.message as string;
            addLogToPhase("scoring", logEntry("info", message));
            break;
          }

          case "scored": {
            const job = event.job as ScoutJob;
            const prog = event.progress as string;
            setLiveJobs((prev) =>
              [...prev, job].sort((a, b) => b.score - a.score),
            );
            setProgress(`Scoring ${prog}`);
            addLogToPhase(
              "scoring",
              logEntry(
                "scored",
                `${job.title} at ${job.company}`,
                `Score: ${job.score}`,
              ),
            );
            break;
          }

          case "score_error": {
            const title = event.title as string;
            addLogToPhase(
              "scoring",
              logEntry("error", `Failed to score: ${title}`, event.error as string),
            );
            break;
          }

          case "complete": {
            const cancelled = event.status === "cancelled";
            setStatus(cancelled ? "cancelled" : "complete");
            const totalScored = (event.total_scored as number) ?? 0;
            const newScored = (event.new_scored as number) ?? 0;
            if (!cancelled) {
              setProgress(`Complete: ${totalScored} matches (${newScored} new)`);
            } else {
              setProgress("Scout cancelled");
            }
            break;
          }

          case "error": {
            const message = event.message as string;
            setErrorMessage(message);
            setStatus("error");
            break;
          }

          case "control": {
            const ctrlStatus = event.status as string;
            if (ctrlStatus === "paused") {
              setStatus("paused");
            } else if (ctrlStatus === "resumed") {
              setStatus("running");
            } else if (ctrlStatus === "cancelled") {
              setStatus("cancelled");
            }
            break;
          }
        }
      };

      ws.onerror = () => {
        setStatus("error");
        setErrorMessage("WebSocket connection failed");
      };

      ws.onclose = () => {
        if (status === "running") {
          // unexpected close
          setStatus((prev) => (prev === "running" ? "error" : prev));
        }
      };
    },
    [updatePhase, addLogToPhase, status],
  );

  const pause = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: "pause" }));
  }, []);

  const resume = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: "resume" }));
  }, []);

  const cancel = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: "cancel" }));
  }, []);

  const reset = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setPhases([]);
    setLiveJobs([]);
    setStatus("idle");
    setProgress("");
    setErrorMessage("");
  }, []);

  return { phases, liveJobs, status, progress, errorMessage, start, pause, resume, cancel, reset };
}

function buildPhaseStartDetail(event: Record<string, unknown>): string | undefined {
  if (event.mode) return `Mode: ${event.mode}`;
  if (event.new_jobs !== undefined) return `${event.new_jobs} new jobs to store`;
  if (event.total !== undefined) return `${event.total} jobs to score`;
  return undefined;
}

function buildPhaseDoneDetail(phase: string, event: Record<string, unknown>): string | undefined {
  if (phase === "ingest") return `${event.total_raw ?? 0} total raw jobs fetched`;
  if (phase === "storing") return `${event.stored ?? 0} new jobs stored`;
  if (phase === "filtering") return `${event.to_score ?? 0} jobs passed filters`;
  if (phase === "scoring") return `${event.scored ?? 0} jobs scored`;
  return undefined;
}
