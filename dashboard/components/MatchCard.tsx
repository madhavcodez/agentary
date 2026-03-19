import Link from "next/link";
import type { Match } from "@/lib/types";
import ScoreBadge from "./ScoreBadge";

interface MatchCardProps {
  match: Match;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "text-gray-400",
  approved: "text-emerald-400",
  rejected: "text-red-400",
  saved: "text-blue-400",
};

export default function MatchCard({ match }: MatchCardProps) {
  const statusColor = STATUS_COLORS[match.status] ?? "text-gray-400";
  const company = match.opportunity?.company ?? "Unknown Company";
  const title = match.opportunity?.title ?? "Unknown Position";
  const rationale = match.rationale
    ? match.rationale.length > 120
      ? match.rationale.slice(0, 120) + "..."
      : match.rationale
    : null;

  return (
    <Link href={`/matches/${match.id}`}>
      <div className="group bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 hover:bg-gray-900/80 transition-all duration-200 cursor-pointer">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-gray-100 truncate group-hover:text-indigo-400 transition-colors">
              {title}
            </h3>
            <p className="text-sm text-gray-400 mt-0.5">{company}</p>
          </div>
          <ScoreBadge score={match.composite_score} size="md" />
        </div>

        <div className="space-y-2 mb-4">
          <ScoreBar label="Semantic" value={match.semantic_score} />
          <ScoreBar label="LLM" value={match.llm_score} />
        </div>

        <div className="flex items-center justify-between">
          <span className={`text-xs font-medium capitalize ${statusColor}`}>
            {match.status}
          </span>
          <span className="text-xs text-gray-600">
            {match.hard_filter_pass === "pass" ? (
              <span className="text-emerald-500">Filters passed</span>
            ) : (
              <span className="text-red-400">Filter: {match.hard_filter_pass}</span>
            )}
          </span>
        </div>

        {rationale && (
          <p className="mt-3 text-xs text-gray-500 leading-relaxed border-t border-gray-800 pt-3">
            {rationale}
          </p>
        )}
      </div>
    </Link>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const barColor =
    pct >= 70
      ? "bg-emerald-500"
      : pct >= 40
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div className="flex items-center gap-3">
      <span className="w-16 text-xs text-gray-500 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-xs text-gray-400 text-right">{Math.round(pct)}</span>
    </div>
  );
}
