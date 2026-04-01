import React from "react";
import { ACTIVITY_ICONS } from "@/lib/constants";
import type { MissionActivity } from "@/lib/types";
import GlassCard from "@/components/ui/GlassCard";

interface ActivityFeedProps {
  activities: MissionActivity[];
  isRunning: boolean;
  isDraft: boolean;
  currentAgentName: string;
  currentAction: string;
  feedRef: React.RefObject<HTMLDivElement>;
}

const ActivityItem = React.memo(function ActivityItem({
  activity,
  index,
}: {
  activity: MissionActivity;
  index: number;
}) {
  return (
    <div
      className="stream-in relative flex items-start gap-3 py-2.5"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      {/* Timeline dot */}
      <span className="absolute -left-4 top-3.5 w-2 h-2 rounded-full bg-emerald-400/60 ring-2 ring-emerald-400/20 flex-shrink-0" />

      {/* Icon */}
      <span className="text-base flex-shrink-0 leading-none mt-0.5">
        {ACTIVITY_ICONS[activity.activity_type] || "\u2022"}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <span className="text-sm text-gray-100">{activity.content}</span>
      </div>

      {/* Timestamp */}
      <span className="text-gray-600 text-xs whitespace-nowrap flex-shrink-0 mt-0.5">
        {activity.created_at
          ? new Date(activity.created_at).toLocaleTimeString()
          : ""}
      </span>
    </div>
  );
});

export default function ActivityFeed({
  activities,
  isRunning,
  isDraft,
  currentAgentName,
  currentAction,
  feedRef,
}: ActivityFeedProps) {
  return (
    <div className="space-y-4" role="tabpanel" aria-label="Live Activity">
      {/* Thinking Indicator */}
      {isRunning && (
        <GlassCard pulse className="p-5">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-blue-400 animate-pulse flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-blue-300">
                  {currentAgentName}
                </span>
                <span className="text-xs text-gray-500">{currentAction}</span>
              </div>
              <div className="text-sm text-gray-300 mt-0.5">
                Researching<span className="thinking-dots"><span>.</span><span>.</span><span>.</span></span>
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Activity Timeline */}
      <div ref={feedRef} className="glass-card rounded-2xl p-4 h-96 overflow-y-auto">
        {activities.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            {isDraft ? "Start the mission to see live activity" : "No activity yet"}
          </div>
        ) : (
          <div className="relative pl-6">
            {/* Timeline connector line */}
            <div className="absolute left-2 top-2 bottom-2 w-px bg-gradient-to-b from-emerald-500/30 to-transparent" />

            {[...activities].reverse().map((activity: MissionActivity, idx: number) => (
              <ActivityItem key={activity.id} activity={activity} index={idx} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
