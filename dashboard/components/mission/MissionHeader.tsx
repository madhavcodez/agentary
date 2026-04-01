import React from "react";
import { STATUS_COLORS } from "@/lib/constants";
import type { MissionLiveStatus, CrewAgent } from "@/lib/types";
import GlassCard from "@/components/ui/GlassCard";

interface MissionHeaderProps {
  status: MissionLiveStatus;
  actionLoading: boolean;
  onStart: () => void;
  onStop: () => void;
  onRerun: () => void;
}

const CrewAgentCard = React.memo(function CrewAgentCard({ agent }: { agent: CrewAgent }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 glass-card rounded-xl transition-all duration-[180ms] hover:shadow-[0_0_20px_4px_rgba(16,185,129,0.12)]">
      <span className="text-lg">{agent.icon || "\u{1F916}"}</span>
      <div>
        <div className="text-sm font-medium text-gray-100">{agent.name}</div>
        <div className="text-xs text-gray-500">{agent.role}</div>
      </div>
    </div>
  );
});

export default function MissionHeader({
  status,
  actionLoading,
  onStart,
  onStop,
  onRerun,
}: MissionHeaderProps) {
  const isRunning = ["running", "queued"].includes(status.status);
  const isDone = ["completed", "failed"].includes(status.status);
  const canStart = ["draft", "paused", "failed"].includes(status.status);
  const startLabel = status.status === "paused" ? "Resume Mission" : "Start Mission";

  return (
    <>
      {/* ── Mission Header ──────────────────────────────────────────── */}
      <GlassCard className="p-8 bg-gradient-to-br from-white/[0.04] to-transparent">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-white">Mission</h1>
              <span className="text-[11px] uppercase tracking-widest text-gray-500">Live Console</span>
            </div>
            <p className="text-sm text-gray-500 mt-2">
              Real-time operations, crew activity, and research findings.
            </p>
            <div className="flex items-center gap-3 mt-4">
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium text-white ${
                  STATUS_COLORS[status.status] || "bg-gray-500"
                }`}
              >
                {status.status}
              </span>
              <span className="text-xs text-gray-300">
                {status.findings_count} findings
                {status.confidence_score != null &&
                  ` · ${Math.round(status.confidence_score * 100)}% confidence`}
              </span>
            </div>
          </div>

          {/* ── Actions ──────────────────────────────────────────────── */}
          <div className="flex gap-2">
            {canStart && (
              <button
                onClick={onStart}
                disabled={actionLoading}
                className="px-4 py-2.5 bg-white text-gray-950 rounded-xl hover:bg-gray-100 disabled:opacity-50 text-sm font-medium shadow-sm"
              >
                {actionLoading ? "Starting..." : startLabel}
              </button>
            )}
            {isRunning && (
              <button
                onClick={onStop}
                disabled={actionLoading}
                className="px-4 py-2.5 bg-rose-500/90 text-white rounded-xl hover:bg-rose-500 disabled:opacity-50 text-sm font-medium"
              >
                {actionLoading ? "Stopping..." : "Stop"}
              </button>
            )}
            {isDone && (
              <button
                onClick={onRerun}
                disabled={actionLoading}
                className="px-4 py-2.5 bg-indigo-500/90 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium"
              >
                {actionLoading ? "Starting..." : "Re-run"}
              </button>
            )}
          </div>
        </div>
      </GlassCard>

      {/* ── Expert Crew Panel ───────────────────────────────────────── */}
      {status.crew && status.crew.agents.length > 0 && (
        <GlassCard className="p-6">
          <h2 className="text-xs font-semibold text-gray-500 mb-4 tracking-widest uppercase">Expert Crew</h2>
          <div className="flex flex-wrap gap-3">
            {status.crew.agents.map((agent: CrewAgent) => (
              <CrewAgentCard key={agent.agent_id} agent={agent} />
            ))}
          </div>
        </GlassCard>
      )}
    </>
  );
}
