"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";
import Spinner from "@/components/ui/Spinner";
import ChannelDot from "./ChannelDot";
import EmailEditor from "./EmailEditor";
import ScriptViewer from "./ScriptViewer";
import LinkedInCopy from "./LinkedInCopy";
import type { Campaign } from "@/lib/types";

interface CampaignRowProps {
  campaign: Campaign;
  expanded: string | null;
  editingEmail: string | undefined;
  emailStatus: "sent" | "draft" | "none";
  callStatus: "completed" | "pending" | "none" | "failed";
  linkedinStatus: "sent" | "draft" | "none";
  actionLoading: Record<string, boolean>;
  onToggleSection: (campaignId: string, section: string) => void;
  onGenerateOutreach: (campaignId: string) => void;
  onSendEmail: (campaignId: string) => void;
  onCallNow: (campaignId: string) => void;
  onEditEmail: (campaignId: string, value: string) => void;
  onCopyClipboard: (text: string) => void;
}

export default function CampaignRow({
  campaign: camp,
  expanded,
  editingEmail,
  emailStatus,
  callStatus,
  linkedinStatus,
  actionLoading,
  onToggleSection,
  onGenerateOutreach,
  onSendEmail,
  onCallNow,
  onEditEmail,
  onCopyClipboard,
}: CampaignRowProps) {
  const company = camp.match?.opportunity?.company ?? "Unknown Company";
  const role = camp.match?.opportunity?.title ?? "Unknown Position";
  const contactName = camp.contact?.name ?? "Unknown";
  const contactPhone = camp.contact?.phone ?? "";

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="min-w-0">
            <Link
              href={`/calls/${camp.id}`}
              className="text-base font-semibold text-gray-100 hover:text-indigo-400 transition-colors"
            >
              {role}
            </Link>
            <p className="text-sm text-gray-400 mt-0.5">{company}</p>
          </div>
          {camp.match?.composite_score != null && (
            <span
              className={cn(
                "px-2 py-0.5 rounded text-xs font-bold border",
                camp.match.composite_score >= 70
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : camp.match.composite_score >= 40
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                    : "bg-red-500/10 text-red-400 border-red-500/20",
              )}
            >
              {Math.round(camp.match.composite_score)}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
            <span>{contactName}</span>
            {contactPhone && (
              <span className="text-xs text-gray-500 font-mono">{contactPhone}</span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <ChannelDot channel="email" status={emailStatus} />
            <ChannelDot channel="call" status={callStatus} />
            <ChannelDot channel="linkedin" status={linkedinStatus} />
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {(["email", "script", "linkedin"] as const).map((section) => {
            const isActive = expanded === section;
            const colors: Record<string, string> = {
              email: isActive
                ? "bg-blue-500/15 border-blue-500/30 text-blue-400"
                : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-300",
              script: isActive
                ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-300",
              linkedin: isActive
                ? "bg-purple-500/15 border-purple-500/30 text-purple-400"
                : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-300",
            };
            const labels: Record<string, string> = {
              email: "Email Draft",
              script: "Call Script",
              linkedin: "LinkedIn",
            };
            return (
              <button
                key={section}
                onClick={() => onToggleSection(camp.id, section)}
                className={cn(
                  "px-2.5 py-1 text-xs rounded-lg border transition-colors",
                  colors[section],
                )}
              >
                {labels[section]}
              </button>
            );
          })}
          <div className="flex-1" />
          {!camp.email_draft && !camp.linkedin_msg && !camp.script_json && (
            <button
              onClick={() => onGenerateOutreach(camp.id)}
              disabled={actionLoading[`outreach_${camp.id}`]}
              className="px-3 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50 border border-indigo-500/20"
            >
              {actionLoading[`outreach_${camp.id}`] ? (
                <>
                  <Spinner size="sm" />
                  Generating...
                </>
              ) : (
                "Generate All Channels"
              )}
            </button>
          )}
        </div>
      </div>

      {expanded === "email" && (
        <div className="border-t border-gray-800 p-5 bg-gray-950/50">
          <h4 className="text-xs font-medium text-blue-400 uppercase tracking-wider mb-3">
            Email Draft
          </h4>
          <EmailEditor
            subject={camp.email_subject}
            body={editingEmail ?? camp.email_draft ?? ""}
            onBodyChange={(v) => onEditEmail(camp.id, v)}
            onSend={() => onSendEmail(camp.id)}
            sending={actionLoading[`email_${camp.id}`] ?? false}
            hasEmail={!!camp.email_draft}
          />
        </div>
      )}

      {expanded === "script" && (
        <div className="border-t border-gray-800 p-5 bg-gray-950/50">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-medium text-emerald-400 uppercase tracking-wider">
              Call Script
            </h4>
            <button
              onClick={() => onCallNow(camp.id)}
              disabled={
                actionLoading[`call_${camp.id}`] ||
                (camp.status !== "pending" && camp.status !== "scheduled")
              }
              className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {actionLoading[`call_${camp.id}`] ? (
                <>
                  <Spinner size="sm" />
                  Calling...
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                  </svg>
                  Call Now
                </>
              )}
            </button>
          </div>
          <ScriptViewer scriptJson={camp.script_json} />
        </div>
      )}

      {expanded === "linkedin" && (
        <div className="border-t border-gray-800 p-5 bg-gray-950/50">
          <h4 className="text-xs font-medium text-purple-400 uppercase tracking-wider mb-3">
            LinkedIn Message
          </h4>
          <LinkedInCopy
            message={camp.linkedin_msg}
            onCopy={onCopyClipboard}
          />
        </div>
      )}
    </div>
  );
}
