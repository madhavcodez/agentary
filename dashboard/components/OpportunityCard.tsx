import Link from "next/link";
import type { Opportunity } from "@/lib/types";

interface OpportunityCardProps {
  opportunity: Opportunity;
}

const SOURCE_COLORS: Record<string, string> = {
  greenhouse: "bg-green-500/10 text-green-400 border-green-500/20",
  lever: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  yc_hn: "bg-orange-500/10 text-orange-400 border-orange-500/20",
};

export default function OpportunityCard({ opportunity }: OpportunityCardProps) {
  const sourceColor =
    SOURCE_COLORS[opportunity.source] ??
    "bg-gray-500/10 text-gray-400 border-gray-500/20";

  const truncatedDescription = opportunity.description
    ? opportunity.description.length > 180
      ? opportunity.description.slice(0, 180) + "..."
      : opportunity.description
    : "No description available.";

  return (
    <Link href={`/opportunities/${opportunity.id}`}>
      <div className="group bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 hover:bg-gray-900/80 transition-all duration-200 cursor-pointer">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-gray-100 truncate group-hover:text-indigo-400 transition-colors">
              {opportunity.title}
            </h3>
            <p className="text-sm text-gray-400 mt-0.5">{opportunity.company}</p>
          </div>
          <span
            className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium ${sourceColor}`}
          >
            {opportunity.source}
          </span>
        </div>

        {opportunity.location && (
          <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-3">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 0115 0z" />
            </svg>
            {opportunity.location}
          </div>
        )}

        <p className="text-sm text-gray-500 leading-relaxed">{truncatedDescription}</p>

        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs text-gray-600">
            {new Date(opportunity.created_at).toLocaleDateString()}
          </span>
          <span className="text-xs text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity">
            View details &rarr;
          </span>
        </div>
      </div>
    </Link>
  );
}
