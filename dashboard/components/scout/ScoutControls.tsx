"use client";

import { cn } from "@/lib/cn";
import type { ScoutMode, ScoutStatus, Skill } from "@/lib/types";
import Button from "@/components/ui/Button";
import SkillChip from "./SkillChip";

interface ScoutControlsProps {
  status: ScoutStatus;
  mode: ScoutMode;
  onModeChange: (mode: ScoutMode) => void;
  skills: Skill[];
  activeSkills: string[];
  onToggleSkill: (name: string) => void;
  progress: string;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onReset: () => void;
}

export default function ScoutControls({
  status,
  mode,
  onModeChange,
  skills,
  activeSkills,
  onToggleSkill,
  progress,
  onStart,
  onPause,
  onResume,
  onCancel,
  onReset,
}: ScoutControlsProps) {
  const isRunning = status === "running";
  const isPaused = status === "paused";
  const isIdle = status === "idle";
  const isDone = status === "complete" || status === "error" || status === "cancelled";

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
      {/* Mode toggle + action buttons */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-1 bg-gray-800/60 rounded-lg p-0.5">
          <button
            type="button"
            disabled={isRunning || isPaused}
            onClick={() => onModeChange("rank_all")}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-medium transition-colors duration-150",
              "disabled:cursor-not-allowed",
              mode === "rank_all"
                ? "bg-gray-700 text-gray-100"
                : "text-gray-400 hover:text-gray-300",
            )}
          >
            All Jobs
          </button>
          <button
            type="button"
            disabled={isRunning || isPaused}
            onClick={() => onModeChange("strict_filter")}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-medium transition-colors duration-150",
              "disabled:cursor-not-allowed",
              mode === "strict_filter"
                ? "bg-gray-700 text-gray-100"
                : "text-gray-400 hover:text-gray-300",
            )}
          >
            Strict Match
          </button>
        </div>

        <div className="flex items-center gap-2">
          {isIdle && (
            <Button variant="primary" size="sm" onClick={onStart}>
              <RadarIcon />
              Start Scout
            </Button>
          )}
          {isRunning && (
            <>
              <Button variant="secondary" size="sm" onClick={onPause}>
                Pause
              </Button>
              <Button variant="danger" size="sm" onClick={onCancel}>
                Cancel
              </Button>
            </>
          )}
          {isPaused && (
            <>
              <Button variant="primary" size="sm" onClick={onResume}>
                Resume
              </Button>
              <Button variant="danger" size="sm" onClick={onCancel}>
                Cancel
              </Button>
            </>
          )}
          {isDone && (
            <Button variant="secondary" size="sm" onClick={onReset}>
              New Scout
            </Button>
          )}
        </div>
      </div>

      {/* Skill chips */}
      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {skills.map((s) => (
            <SkillChip
              key={s.name}
              name={s.name}
              active={activeSkills.includes(s.name)}
              onToggle={onToggleSkill}
              disabled={isRunning || isPaused}
            />
          ))}
        </div>
      )}

      {/* Progress text */}
      {progress && (
        <div className="flex items-center gap-2">
          {(isRunning || isPaused) && (
            <div className="w-3 h-3 rounded-full border-[1.5px] border-gray-700 border-t-indigo-400 animate-spin" />
          )}
          {status === "complete" && <CheckCircleIcon />}
          {status === "error" && <ErrorCircleIcon />}
          {status === "cancelled" && <CancelCircleIcon />}
          <span className="text-xs text-gray-400">{progress}</span>
        </div>
      )}
    </div>
  );
}

function RadarIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.348 14.652a3.75 3.75 0 010-5.304m5.304 0a3.75 3.75 0 010 5.304m-7.425 2.121a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.788m13.788 0c3.808 3.808 3.808 9.98 0 13.788M12 12h.008v.008H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function ErrorCircleIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  );
}

function CancelCircleIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
    </svg>
  );
}
