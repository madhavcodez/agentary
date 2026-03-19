import Link from "next/link";
import type { Campaign } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

interface CampaignCardProps {
  campaign: Campaign;
  onCallNow?: (id: string) => void;
  callLoading?: boolean;
}

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

export default function CampaignCard({ campaign, onCallNow, callLoading }: CampaignCardProps) {
  const company = campaign.match?.opportunity?.company ?? "Unknown Company";
  const title = campaign.match?.opportunity?.title ?? "Unknown Position";
  const contactName = campaign.contact?.name ?? "Unknown Contact";
  const contactPhone = campaign.contact?.phone ?? "No phone";
  const score = campaign.match?.composite_score ?? 0;
  const statusStyle = STATUS_STYLES[campaign.status] ?? STATUS_STYLES.pending;
  const canCall = campaign.status === "pending" || campaign.status === "scheduled";

  return (
    <div className="group bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 hover:bg-gray-900/80 transition-all duration-200">
      <div className="flex items-start justify-between gap-4 mb-3">
        <Link href={`/calls/${campaign.id}`} className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-gray-100 truncate group-hover:text-indigo-400 transition-colors">
            {title}
          </h3>
          <p className="text-sm text-gray-400 mt-0.5">{company}</p>
        </Link>
        <ScoreBadge score={score} size="sm" />
      </div>

      <div className="flex items-center gap-2 mb-3">
        <svg className="w-4 h-4 text-gray-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
        </svg>
        <span className="text-sm text-gray-300 truncate">{contactName}</span>
        <span className="text-xs text-gray-500">{contactPhone}</span>
      </div>

      <div className="flex items-center justify-between mb-3">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium capitalize ${statusStyle}`}>
          {formatStatus(campaign.status)}
        </span>
        <span className="text-xs text-gray-500">
          {campaign.attempt_count}/{campaign.max_attempts} attempts
        </span>
      </div>

      {campaign.scheduled_at && campaign.status === "scheduled" && (
        <p className="text-xs text-blue-400 mb-3">
          Scheduled: {new Date(campaign.scheduled_at).toLocaleString()}
        </p>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-gray-800">
        <Link
          href={`/calls/${campaign.id}`}
          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          View details &rarr;
        </Link>
        {canCall && onCallNow && (
          <button
            onClick={(e) => {
              e.preventDefault();
              onCallNow(campaign.id);
            }}
            disabled={callLoading}
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
            </svg>
            {callLoading ? "Calling..." : "Call Now"}
          </button>
        )}
      </div>
    </div>
  );
}
