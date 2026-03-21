"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";
import EmptyState from "@/components/ui/EmptyState";
import ConversationTimeline from "./ConversationTimeline";
import type { OutreachData } from "@/lib/hooks/useOutreachData";

const OUTCOME_MAP: Record<string, string> = {
  completed:
    "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  pending: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  in_progress:
    "bg-amber-500/10 text-amber-400 border-amber-500/20",
  scheduled: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
};

interface ConversationsTabProps {
  data: OutreachData;
}

export default function ConversationsTab({ data }: ConversationsTabProps) {
  const activeConversations = data.campaigns
    .filter((c) => c.attempt_count > 0)
    .sort(
      (a, b) =>
        new Date(b.updated_at).getTime() -
        new Date(a.updated_at).getTime(),
    );

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-200 mb-4">
        Active Conversations ({activeConversations.length})
      </h2>

      {activeConversations.length === 0 ? (
        <EmptyState
          icon={
            <svg className="w-10 h-10 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
            </svg>
          }
          title="No active conversations yet."
          description="Campaigns with call attempts or sent emails will appear here."
        />
      ) : (
        <div className="space-y-3">
          {activeConversations.map((camp) => {
            const company =
              camp.match?.opportunity?.company ?? "Unknown";
            const role =
              camp.match?.opportunity?.title ?? "Unknown";
            const contactName = camp.contact?.name ?? "Unknown";
            const isExpanded =
              data.expandedCampaigns[camp.id] === "timeline";

            const events: {
              type: string;
              label: string;
              time: string;
              color: string;
            }[] = [];
            if (camp.email_draft) {
              events.push({
                type: "email",
                label: "Email draft created",
                time: camp.updated_at,
                color: "blue",
              });
            }
            if (camp.attempt_count > 0) {
              events.push({
                type: "call",
                label: `Call attempted (${camp.attempt_count}/${camp.max_attempts})`,
                time: camp.updated_at,
                color: "emerald",
              });
            }
            if (camp.linkedin_msg) {
              events.push({
                type: "linkedin",
                label: "LinkedIn message drafted",
                time: camp.updated_at,
                color: "purple",
              });
            }

            return (
              <div
                key={camp.id}
                className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
              >
                <div className="p-5">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div>
                      <Link
                        href={`/calls/${camp.id}`}
                        className="text-sm font-semibold text-gray-100 hover:text-indigo-400 transition-colors"
                      >
                        {role} at {company}
                      </Link>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {contactName} -- {camp.attempt_count}/
                        {camp.max_attempts} attempts
                      </p>
                    </div>
                    <span
                      className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium capitalize",
                        OUTCOME_MAP[camp.status] ?? OUTCOME_MAP.pending,
                      )}
                    >
                      {camp.status.replace(/_/g, " ")}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 mb-3">
                    {events.map((ev, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-1.5"
                      >
                        <div
                          className={cn(
                            "w-2 h-2 rounded-full",
                            ev.color === "blue"
                              ? "bg-blue-400"
                              : ev.color === "emerald"
                                ? "bg-emerald-400"
                                : "bg-purple-400",
                          )}
                        />
                        <span className="text-[10px] text-gray-500">
                          {ev.label}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        data.toggleCampaignSection(camp.id, "timeline")
                      }
                      className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      {isExpanded
                        ? "Hide timeline"
                        : "View full timeline"}
                    </button>
                    <div className="flex-1" />
                    <Link
                      href={`/calls/${camp.id}`}
                      className="text-xs text-gray-400 hover:text-gray-300 transition-colors"
                    >
                      Open details
                    </Link>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-gray-800 p-5 bg-gray-950/50">
                    <ConversationTimeline events={events} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
