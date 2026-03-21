"use client";

import EmptyState from "@/components/ui/EmptyState";
import AutopilotControl from "./AutopilotControl";
import ResearchCard from "./ResearchCard";
import type { OutreachData } from "@/lib/hooks/useOutreachData";

interface IdeasTabProps {
  data: OutreachData;
}

export default function IdeasTab({ data }: IdeasTabProps) {
  return (
    <div>
      <AutopilotControl
        status={data.autopilotStatus}
        running={data.autopilotRunning}
        onRun={data.handleRunAutopilot}
      />

      <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
        Top Matches for Research
      </h3>

      {data.matches.length === 0 ? (
        <EmptyState
          title="No matches yet."
          description="Run Scout from the Profile page first."
        />
      ) : (
        <div className="space-y-3">
          {data.matches.slice(0, 10).map((m) => (
            <ResearchCard
              key={m.id}
              match={m}
              research={data.researchResults[m.id]}
              isResearching={data.researchLoading[m.id] ?? false}
              onResearch={data.handleResearch}
              onToggleResearch={(matchId) => {
                data.setResearchResults((prev) => {
                  const next = { ...prev };
                  delete next[matchId];
                  return next;
                });
              }}
              onQueueContact={(form) => {
                data.setContactForm(form);
                data.setTab("networking");
                data.setShowAddForm(true);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
