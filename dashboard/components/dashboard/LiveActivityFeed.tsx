"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { LiveEvent } from "@/lib/types";

interface LiveActivityFeedProps {
  events: LiveEvent[];
}

const EVENT_ICONS: Record<string, string> = {
  "scout.phase.start": "\uD83D\uDD0D",
  "scout.phase.done": "\u2705",
  "scout.source.update": "\uD83D\uDCE1",
  "scout.job.scored": "\uD83C\uDFAF",
  "scout.complete": "\uD83C\uDFC1",
  "workflow.start": "\u26A1",
  "workflow.step": "\u2699\uFE0F",
  "workflow.complete": "\uD83C\uDF89",
  "monitor.check.start": "\uD83D\uDD04",
  "monitor.check.done": "\u2714\uFE0F",
  "monitor.change.detected": "\uD83D\uDCA1",
  "alert.created": "\uD83D\uDD14",
  "system.status": "\uD83D\uDCBB",
  "system.error": "\u26A0\uFE0F",
};

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function eventMessage(event: LiveEvent): string {
  const d = event.data;
  switch (event.event_type) {
    case "scout.phase.start":
      return `Scout phase started: ${d.phase ?? ""}`;
    case "scout.phase.done":
      return `Scout phase done: ${d.phase ?? ""}`;
    case "scout.job.scored":
      return `Scored: ${d.title ?? ""} at ${d.company ?? ""} (${d.score ?? ""})`;
    case "monitor.check.start":
      return `Checking: ${d.monitor_name ?? ""}`;
    case "monitor.check.done":
      return `${d.monitor_name ?? ""}: ${d.changed ? "Change detected" : "No change"}`;
    case "monitor.change.detected":
      return `Change detected: ${d.summary ?? ""}`;
    case "alert.created":
      return `Alert: ${d.title ?? ""}`;
    case "workflow.start":
      return `Workflow started: ${d.workflow_name ?? ""}`;
    case "workflow.step":
      return `Step: ${d.node_label ?? d.node_id ?? ""}`;
    case "workflow.complete":
      return `Workflow complete: ${d.workflow_name ?? ""}`;
    default:
      return d.message as string ?? event.event_type;
  }
}

export default function LiveActivityFeed({ events }: LiveActivityFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const lastScrollTop = useRef(0);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events.length, autoScroll]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
    // Pause auto-scroll if user scrolled up
    if (el.scrollTop < lastScrollTop.current && !atBottom) {
      setAutoScroll(false);
    } else if (atBottom) {
      setAutoScroll(true);
    }
    lastScrollTop.current = el.scrollTop;
  }, []);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg flex flex-col">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-200">Live Activity Feed</h2>
        <div className="flex items-center gap-2">
          {!autoScroll && (
            <button
              onClick={() => setAutoScroll(true)}
              className="text-xs text-indigo-400 hover:text-indigo-300"
            >
              Resume auto-scroll
            </button>
          )}
          <div className={`w-2 h-2 rounded-full ${events.length > 0 ? "bg-emerald-400 animate-pulse" : "bg-gray-600"}`} />
        </div>
      </div>
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-[200px] max-h-[400px] overflow-y-auto px-4 py-2 space-y-1"
      >
        {events.length === 0 && (
          <div className="py-8 text-center text-sm text-gray-500">
            Waiting for activity...
          </div>
        )}
        {events.map((event, idx) => (
          <div
            key={event.event_id ?? idx}
            className="flex items-start gap-2 py-1.5 animate-fade-in"
          >
            <span className="text-xs text-gray-500 font-mono shrink-0 mt-0.5">
              {formatTime(event.timestamp)}
            </span>
            <span className="shrink-0">{EVENT_ICONS[event.event_type] ?? "\u25CF"}</span>
            <span className="text-sm text-gray-300 leading-snug">
              {eventMessage(event)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
