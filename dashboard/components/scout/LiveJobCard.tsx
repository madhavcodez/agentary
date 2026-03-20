"use client";

import { cn } from "@/lib/cn";
import type { ScoutJob } from "@/lib/types";

interface LiveJobCardProps {
  job: ScoutJob;
  index: number;
}

export default function LiveJobCard({ job, index }: LiveJobCardProps) {
  const scoreColor =
    job.score >= 70
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      : job.score >= 40
        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
        : "bg-red-500/10 text-red-400 border-red-500/20";

  const rationale =
    job.rationale && job.rationale.length > 100
      ? job.rationale.slice(0, 100) + "..."
      : job.rationale;

  return (
    <div
      className={cn(
        "bg-gray-900 border border-gray-800 rounded-xl p-4",
        "hover:border-gray-700 transition-all duration-200",
        "animate-slideIn",
      )}
      style={{ animationDelay: `${Math.min(index * 30, 300)}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold text-gray-100 truncate">
            {job.title}
          </h4>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-xs text-indigo-400 truncate">{job.company}</p>
            {job.location && (
              <>
                <span className="text-gray-700">·</span>
                <p className="text-xs text-gray-500 truncate">{job.location}</p>
              </>
            )}
          </div>
        </div>

        <span
          className={cn(
            "shrink-0 inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold border",
            scoreColor,
          )}
        >
          {Math.round(job.score)}
        </span>
      </div>

      {rationale && (
        <p className="mt-2 text-xs text-gray-500 leading-relaxed line-clamp-2">
          {rationale}
        </p>
      )}
    </div>
  );
}
