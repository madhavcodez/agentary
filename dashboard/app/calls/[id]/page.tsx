"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  fetchCampaign,
  fetchCampaignLogs,
  triggerCall,
  generateScript,
  sendEmail,
  generateOutreachPackage,
  getResearch,
} from "@/lib/api";
import type { Campaign, CallLog, ResearchResult } from "@/lib/types";
import ScoreBadge from "@/components/ScoreBadge";
import CallLogTimeline from "@/components/CallLogTimeline";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  scheduled: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  in_progress: "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse",
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
  cancelled: "bg-gray-500/10 text-gray-500 border-gray-500/20",
};

function formatStatus(status: string): string {
  return status.replace(/_/g, " ");
}

function Spinner({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <div
      className={`border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin ${className}`}
    />
  );
}

function Toast({
  message,
  type,
  onClose,
}: {
  message: string;
  type: "success" | "error" | "info";
  onClose: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bg =
    type === "success"
      ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
      : type === "error"
        ? "bg-red-500/15 border-red-500/30 text-red-400"
        : "bg-blue-500/15 border-blue-500/30 text-blue-400";

  return (
    <div className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-xl border text-sm font-medium shadow-lg ${bg}`}>
      {message}
    </div>
  );
}

export default function CampaignDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [logs, setLogs] = useState<CallLog[]>([]);
  const [research, setResearch] = useState<ResearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(true);
  const [callLoading, setCallLoading] = useState(false);
  const [scriptLoading, setScriptLoading] = useState(false);
  const [emailSending, setEmailSending] = useState(false);
  const [outreachGenerating, setOutreachGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scriptExpanded, setScriptExpanded] = useState(false);
  const [emailExpanded, setEmailExpanded] = useState(false);
  const [linkedinExpanded, setLinkedinExpanded] = useState(false);
  const [timelineExpanded, setTimelineExpanded] = useState(false);
  const [researchExpanded, setResearchExpanded] = useState(false);
  const [editedEmail, setEditedEmail] = useState<string | null>(null);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error" | "info";
  } | null>(null);

  const loadCampaign = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCampaign(id);
      setCampaign(data);
      if (data.email_draft && editedEmail === null) {
        setEditedEmail(data.email_draft);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch campaign"
      );
    } finally {
      setLoading(false);
    }
  }, [id, editedEmail]);

  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const data = await fetchCampaignLogs(id);
      setLogs(data);
    } catch {
      // Logs may not exist yet
    } finally {
      setLogsLoading(false);
    }
  }, [id]);

  const loadResearch = useCallback(async (matchId: string) => {
    try {
      const data = await getResearch(matchId);
      setResearch(data);
    } catch {
      // Research may not exist yet
    }
  }, []);

  useEffect(() => {
    loadCampaign();
    loadLogs();
  }, [loadCampaign, loadLogs]);

  useEffect(() => {
    if (campaign?.match_id) {
      loadResearch(campaign.match_id);
    }
  }, [campaign?.match_id, loadResearch]);

  async function handleCallNow() {
    setCallLoading(true);
    setError(null);
    try {
      const updated = await triggerCall(id);
      setCampaign(updated);
      loadLogs();
      setToast({ message: "Call initiated", type: "success" });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to trigger call"
      );
    } finally {
      setCallLoading(false);
    }
  }

  async function handleRegenerateScript() {
    setScriptLoading(true);
    setError(null);
    try {
      const updated = await generateScript(id);
      setCampaign(updated);
      setScriptExpanded(true);
      setToast({ message: "Script generated", type: "success" });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate script"
      );
    } finally {
      setScriptLoading(false);
    }
  }

  async function handleSendEmail() {
    setEmailSending(true);
    try {
      const updated = await sendEmail(id);
      setCampaign(updated);
      setToast({ message: "Email sent successfully", type: "success" });
    } catch (err) {
      setToast({
        message:
          err instanceof Error ? err.message : "Failed to send email",
        type: "error",
      });
    } finally {
      setEmailSending(false);
    }
  }

  async function handleGenerateOutreach() {
    setOutreachGenerating(true);
    try {
      const updated = await generateOutreachPackage(id);
      setCampaign(updated);
      if (updated.email_draft) {
        setEditedEmail(updated.email_draft);
      }
      setToast({
        message: "Outreach package generated",
        type: "success",
      });
    } catch (err) {
      setToast({
        message:
          err instanceof Error
            ? err.message
            : "Failed to generate outreach package",
        type: "error",
      });
    } finally {
      setOutreachGenerating(false);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setToast({ message: "Copied to clipboard", type: "info" });
  }

  if (loading) {
    return (
      <div className="max-w-4xl">
        <div className="text-center py-16">
          <Spinner className="w-6 h-6 mx-auto" />
          <p className="text-sm text-gray-500 mt-3">Loading campaign...</p>
        </div>
      </div>
    );
  }

  if (error && !campaign) {
    return (
      <div className="max-w-4xl">
        <Link
          href="/calls"
          className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors mb-6"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Back to Calls
        </Link>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!campaign) return null;

  const company = campaign.match?.opportunity?.company ?? "Unknown Company";
  const title = campaign.match?.opportunity?.title ?? "Unknown Position";
  const contactName = campaign.contact?.name ?? "Unknown Contact";
  const contactPhone = campaign.contact?.phone ?? "No phone";
  const contactEmail = campaign.contact?.email ?? null;
  const contactTitle = campaign.contact?.title ?? null;
  const score = campaign.match?.composite_score ?? 0;
  const statusStyle = STATUS_STYLES[campaign.status] ?? STATUS_STYLES.pending;
  const canCall = campaign.status === "pending" || campaign.status === "scheduled";
  const isTerminal = campaign.status === "completed" || campaign.status === "failed" || campaign.status === "cancelled";

  const scriptJson = campaign.script_json;
  const hasScript = scriptJson !== null && Object.keys(scriptJson).length > 0;
  const hasEmail = !!campaign.email_draft;
  const hasLinkedin = !!campaign.linkedin_msg;
  const hasAnyOutreach = hasScript || hasEmail || hasLinkedin;

  // Build multi-channel timeline events
  const channelEvents: { type: string; label: string; time: string; color: string; icon: string }[] = [];
  if (hasEmail) {
    channelEvents.push({
      type: "email",
      label: `Email draft: "${campaign.email_subject || "No subject"}"`,
      time: campaign.updated_at,
      color: "blue",
      icon: "M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75",
    });
  }
  if (campaign.attempt_count > 0) {
    channelEvents.push({
      type: "call",
      label: `Call attempted (${campaign.attempt_count}/${campaign.max_attempts})`,
      time: campaign.updated_at,
      color: "emerald",
      icon: "M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z",
    });
  }
  if (hasLinkedin) {
    channelEvents.push({
      type: "linkedin",
      label: "LinkedIn message drafted",
      time: campaign.updated_at,
      color: "purple",
      icon: "M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m9.364-9.364a4.5 4.5 0 010 6.364l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757",
    });
  }

  return (
    <div className="max-w-4xl">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      <Link
        href="/calls"
        className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to Calls
      </Link>

      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Campaign Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">{title}</h1>
            <p className="text-base text-gray-400 mt-1">{company}</p>
          </div>
          <ScoreBadge score={score} size="lg" />
        </div>

        {/* Contact info */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
            <span className="text-sm font-medium text-gray-200">{contactName}</span>
            {contactTitle && (
              <span className="text-xs text-gray-500">{contactTitle}</span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400">
            <span className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
              </svg>
              {contactPhone}
            </span>
            {contactEmail && (
              <span className="flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                </svg>
                {contactEmail}
              </span>
            )}
          </div>
        </div>

        {/* Status + meta */}
        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400 mb-5">
          <span className={`inline-flex items-center px-2.5 py-1 rounded-md border text-xs font-medium capitalize ${statusStyle}`}>
            {formatStatus(campaign.status)}
          </span>
          <span className="text-gray-700">|</span>
          <span>{campaign.attempt_count}/{campaign.max_attempts} attempts</span>
          <span className="text-gray-700">|</span>
          <span>Priority: {campaign.priority}</span>
          {campaign.scheduled_at && (
            <>
              <span className="text-gray-700">|</span>
              <span>Scheduled: {new Date(campaign.scheduled_at).toLocaleString()}</span>
            </>
          )}
          <span className="text-gray-700">|</span>
          <span className="text-gray-500">
            Created {new Date(campaign.created_at).toLocaleDateString()}
          </span>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 pt-5 border-t border-gray-800 flex-wrap">
          {canCall && (
            <button
              onClick={handleCallNow}
              disabled={callLoading}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {callLoading ? (
                <>
                  <Spinner />
                  Calling...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                  </svg>
                  Call Now
                </>
              )}
            </button>
          )}
          <button
            onClick={handleRegenerateScript}
            disabled={scriptLoading}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {scriptLoading ? (
              <>
                <Spinner />
                Generating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
                </svg>
                {hasScript ? "Regenerate Script" : "Generate Script"}
              </>
            )}
          </button>
          {!hasAnyOutreach && (
            <button
              onClick={handleGenerateOutreach}
              disabled={outreachGenerating}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {outreachGenerating ? (
                <>
                  <Spinner />
                  Generating All...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                  </svg>
                  Generate All Channels
                </>
              )}
            </button>
          )}
          {!isTerminal && (
            <Link
              href="/contacts"
              className="ml-auto px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 font-medium rounded-lg transition-colors"
            >
              Manage Contacts
            </Link>
          )}
        </div>
      </div>

      {/* Multi-Channel Timeline */}
      {channelEvents.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl mb-6">
          <button
            onClick={() => setTimelineExpanded((prev) => !prev)}
            className="w-full flex items-center justify-between px-6 py-4 text-left"
          >
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Multi-Channel Timeline
              </h2>
              <span className="text-xs text-gray-500">
                {channelEvents.length} event{channelEvents.length !== 1 ? "s" : ""}
              </span>
            </div>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${timelineExpanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          {timelineExpanded && (
            <div className="px-6 pb-6 border-t border-gray-800 pt-4">
              <div className="relative pl-6">
                <div className="absolute left-2 top-1 bottom-1 w-px bg-gray-800" />
                {channelEvents.map((ev, i) => {
                  const dotColor =
                    ev.color === "blue"
                      ? "bg-blue-400"
                      : ev.color === "emerald"
                        ? "bg-emerald-400"
                        : "bg-purple-400";
                  const textColor =
                    ev.color === "blue"
                      ? "text-blue-400"
                      : ev.color === "emerald"
                        ? "text-emerald-400"
                        : "text-purple-400";

                  return (
                    <div key={i} className="relative pb-5 last:pb-0">
                      <div className={`absolute left-[-16px] top-1 w-2.5 h-2.5 rounded-full border-2 border-gray-950 ${dotColor}`} />
                      <div className="flex items-start gap-3">
                        <svg
                          className={`w-4 h-4 shrink-0 mt-0.5 ${textColor}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={1.5}
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d={ev.icon} />
                        </svg>
                        <div>
                          <p className="text-sm text-gray-300">{ev.label}</p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {new Date(ev.time).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Email Draft Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl mb-6">
        <button
          onClick={() => setEmailExpanded((prev) => !prev)}
          className="w-full flex items-center justify-between px-6 py-4 text-left"
        >
          <div className="flex items-center gap-3">
            <svg
              className={`w-4 h-4 ${hasEmail ? "text-blue-400" : "text-gray-600"}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
            </svg>
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              Email Draft
            </h2>
            {hasEmail && (
              <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-blue-500/15 text-blue-400 border border-blue-500/25">
                READY
              </span>
            )}
          </div>
          <svg
            className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${emailExpanded ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
        {emailExpanded && (
          <div className="px-6 pb-6 border-t border-gray-800 pt-4">
            {hasEmail ? (
              <>
                {campaign.email_subject && (
                  <div className="mb-3">
                    <span className="text-[10px] text-gray-500 uppercase">Subject:</span>
                    <p className="text-sm text-gray-200 mt-0.5">{campaign.email_subject}</p>
                  </div>
                )}
                <textarea
                  value={editedEmail ?? campaign.email_draft ?? ""}
                  onChange={(e) => setEditedEmail(e.target.value)}
                  rows={8}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none resize-none font-mono mb-3"
                />
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSendEmail}
                    disabled={emailSending}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                  >
                    {emailSending ? (
                      <>
                        <Spinner />
                        Sending...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                        </svg>
                        Send Email
                      </>
                    )}
                  </button>
                  {editedEmail !== campaign.email_draft && (
                    <span className="text-xs text-amber-400">Unsaved edits</span>
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-gray-600">
                No email draft yet. Click &quot;Generate All Channels&quot; above to create one.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Call Script */}
      {hasScript && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl mb-6">
          <button
            onClick={() => setScriptExpanded((prev) => !prev)}
            className="w-full flex items-center justify-between px-6 py-4 text-left"
          >
            <div className="flex items-center gap-3">
              <svg
                className="w-4 h-4 text-emerald-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
              </svg>
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Call Script
              </h2>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
                READY
              </span>
            </div>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${scriptExpanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          {scriptExpanded && (
            <div className="px-6 pb-6 border-t border-gray-800 pt-4">
              <ScriptDisplay script={scriptJson!} />
            </div>
          )}
        </div>
      )}

      {/* LinkedIn Message Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl mb-6">
        <button
          onClick={() => setLinkedinExpanded((prev) => !prev)}
          className="w-full flex items-center justify-between px-6 py-4 text-left"
        >
          <div className="flex items-center gap-3">
            <svg
              className={`w-4 h-4 ${hasLinkedin ? "text-purple-400" : "text-gray-600"}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m9.364-9.364a4.5 4.5 0 010 6.364l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757" />
            </svg>
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              LinkedIn Message
            </h2>
            {hasLinkedin && (
              <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-purple-500/15 text-purple-400 border border-purple-500/25">
                READY
              </span>
            )}
          </div>
          <svg
            className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${linkedinExpanded ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
        {linkedinExpanded && (
          <div className="px-6 pb-6 border-t border-gray-800 pt-4">
            {hasLinkedin ? (
              <>
                <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 text-sm text-gray-300 whitespace-pre-wrap mb-3">
                  {campaign.linkedin_msg}
                </div>
                <button
                  onClick={() => copyToClipboard(campaign.linkedin_msg!)}
                  className="px-4 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 border border-purple-500/20"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                  </svg>
                  Copy to Clipboard
                </button>
              </>
            ) : (
              <p className="text-sm text-gray-600">
                No LinkedIn message yet. Click &quot;Generate All Channels&quot; above to create one.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Match Rationale */}
      {campaign.match?.rationale && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
            Match Rationale
          </h2>
          <p className="text-sm text-gray-400 leading-relaxed">
            {campaign.match.rationale}
          </p>
        </div>
      )}

      {/* Research Intel Section */}
      {research && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl mb-6">
          <button
            onClick={() => setResearchExpanded((prev) => !prev)}
            className="w-full flex items-center justify-between px-6 py-4 text-left"
          >
            <div className="flex items-center gap-3">
              <svg
                className="w-4 h-4 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
              </svg>
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                Research Intel
              </h2>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-indigo-500/15 text-indigo-400 border border-indigo-500/25">
                {research.quality_score}% QUALITY
              </span>
            </div>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${researchExpanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          {researchExpanded && (
            <div className="border-t border-gray-800">
              {/* Company intel */}
              {Object.keys(research.company_intel).length > 0 && (
                <div className="px-6 py-4 border-b border-gray-800/50">
                  <h3 className="text-xs font-medium text-indigo-400 uppercase tracking-wider mb-3">
                    Company Intelligence
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(research.company_intel).map(([key, value]) => (
                      <div key={key} className="bg-gray-800/30 rounded-lg p-3">
                        <p className="text-[10px] text-gray-500 uppercase mb-1">
                          {key.replace(/_/g, " ")}
                        </p>
                        <p className="text-xs text-gray-300">
                          {typeof value === "string" ? value : JSON.stringify(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Discovered contacts */}
              {research.contacts_found.length > 0 && (
                <div className="px-6 py-4 border-b border-gray-800/50">
                  <h3 className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-3">
                    Discovered Contacts ({research.contacts_found.length})
                  </h3>
                  <div className="space-y-2">
                    {research.contacts_found.map((contact, i) => (
                      <div key={i} className="flex items-center justify-between bg-gray-800/30 rounded-lg p-3">
                        <div>
                          <p className="text-sm text-gray-200">{String(contact.name || "Unknown")}</p>
                          <p className="text-xs text-gray-500">
                            {String(contact.title || "")}{" "}
                            {contact.email ? `-- ${String(contact.email)}` : ""}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sources */}
              {research.sources_used.length > 0 && (
                <div className="px-6 py-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] text-gray-500 uppercase">Sources:</span>
                    {research.sources_used.map((src, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-[10px] text-gray-400"
                      >
                        {src}
                      </span>
                    ))}
                    <span className="text-[10px] text-gray-600 ml-2">
                      Researched {new Date(research.researched_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Call Log Timeline */}
      <div className="mb-6">
        <h2 className="text-base font-semibold text-gray-200 mb-4">
          Call History
        </h2>
        {logsLoading ? (
          <div className="text-center py-8">
            <Spinner className="w-6 h-6 mx-auto" />
            <p className="text-sm text-gray-500 mt-3">Loading call logs...</p>
          </div>
        ) : (
          <CallLogTimeline logs={logs} />
        )}
      </div>
    </div>
  );
}

function ScriptDisplay({ script }: { script: Record<string, unknown> }) {
  const sections = Object.entries(script);

  return (
    <div className="space-y-4">
      {sections.map(([key, value]) => (
        <div key={key}>
          <h3 className="text-sm font-medium text-indigo-400 capitalize mb-2">
            {key.replace(/_/g, " ")}
          </h3>
          <ScriptValue value={value} />
        </div>
      ))}
    </div>
  );
}

function ScriptValue({ value }: { value: unknown }) {
  if (typeof value === "string") {
    return (
      <p className="text-sm text-gray-300 leading-relaxed bg-gray-800/50 border border-gray-700 rounded-lg p-3">
        {value}
      </p>
    );
  }

  if (Array.isArray(value)) {
    return (
      <ul className="space-y-1.5">
        {value.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
            <span className="text-indigo-400 mt-0.5 shrink-0">&#8226;</span>
            {typeof item === "string" ? (
              item
            ) : (
              <pre className="text-xs text-gray-400 bg-gray-800/50 border border-gray-700 rounded p-2 overflow-x-auto w-full">
                {JSON.stringify(item, null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof value === "object" && value !== null) {
    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k} className="mb-2 last:mb-0">
            <span className="text-xs font-medium text-gray-400 capitalize">
              {k.replace(/_/g, " ")}:
            </span>
            <span className="text-sm text-gray-300 ml-2">{String(v)}</span>
          </div>
        ))}
      </div>
    );
  }

  return <p className="text-sm text-gray-300">{String(value)}</p>;
}
