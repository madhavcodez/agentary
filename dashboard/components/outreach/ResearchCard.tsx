"use client";

import { cn } from "@/lib/cn";
import Spinner from "@/components/ui/Spinner";
import type { Match, ResearchResult } from "@/lib/types";
import type { ContactFormState } from "@/lib/hooks/useOutreachData";

interface ResearchCardProps {
  match: Match;
  research: ResearchResult | undefined;
  isResearching: boolean;
  onResearch: (matchId: string) => void;
  onToggleResearch: (matchId: string) => void;
  onQueueContact: (form: ContactFormState) => void;
}

export default function ResearchCard({
  match,
  research,
  isResearching,
  onResearch,
  onToggleResearch,
  onQueueContact,
}: ResearchCardProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4 mb-2">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "px-2 py-0.5 rounded text-xs font-bold border",
                match.composite_score >= 70
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : match.composite_score >= 40
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                    : "bg-red-500/10 text-red-400 border-red-500/20",
              )}
            >
              {Math.round(match.composite_score)}
            </span>
            <div>
              <h4 className="text-sm font-semibold text-gray-100">
                {match.opportunity?.title}
              </h4>
              <p className="text-xs text-indigo-400">
                {match.opportunity?.company}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              if (research) {
                onToggleResearch(match.id);
              } else {
                onResearch(match.id);
              }
            }}
            disabled={isResearching}
            className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            {isResearching ? (
              <>
                <Spinner size="sm" />
                Researching...
              </>
            ) : research ? (
              "Hide Research"
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                </svg>
                Deep Research
              </>
            )}
          </button>
        </div>
        {match.rationale && (
          <p className="text-xs text-gray-500 mt-2 line-clamp-2">
            {match.rationale}
          </p>
        )}
      </div>

      {research && (
        <div className="border-t border-gray-800 bg-gray-950/50">
          {/* Quality bar */}
          <div className="px-5 py-3 flex items-center gap-3 border-b border-gray-800/50">
            <span className="text-[10px] text-gray-500 uppercase">
              Research Quality:
            </span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full",
                  research.quality_score >= 70
                    ? "bg-emerald-400"
                    : research.quality_score >= 40
                      ? "bg-amber-400"
                      : "bg-red-400",
                )}
                style={{
                  width: `${Math.min(research.quality_score, 100)}%`,
                }}
              />
            </div>
            <span className="text-xs text-gray-400 font-mono">
              {research.quality_score}%
            </span>
          </div>

          {/* Company intel */}
          {Object.keys(research.company_intel).length > 0 && (
            <div className="px-5 py-4 border-b border-gray-800/50">
              <h5 className="text-xs font-medium text-indigo-400 uppercase tracking-wider mb-3">
                Company Intelligence
              </h5>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(research.company_intel).map(
                  ([key, value]) => (
                    <div
                      key={key}
                      className="bg-gray-800/30 rounded-lg p-3"
                    >
                      <p className="text-[10px] text-gray-500 uppercase mb-1">
                        {key.replace(/_/g, " ")}
                      </p>
                      <p className="text-xs text-gray-300">
                        {typeof value === "string"
                          ? value
                          : JSON.stringify(value)}
                      </p>
                    </div>
                  ),
                )}
              </div>
            </div>
          )}

          {/* Discovered contacts */}
          {research.contacts_found.length > 0 && (
            <div className="px-5 py-4 border-b border-gray-800/50">
              <h5 className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-3">
                Discovered Contacts ({research.contacts_found.length})
              </h5>
              <div className="space-y-2">
                {research.contacts_found.map((contact, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between bg-gray-800/30 rounded-lg p-3"
                  >
                    <div>
                      <p className="text-sm text-gray-200">
                        {String(contact.name || "Unknown")}
                      </p>
                      <p className="text-xs text-gray-500">
                        {String(contact.title || "")}{" "}
                        {contact.email
                          ? `-- ${String(contact.email)}`
                          : ""}
                      </p>
                    </div>
                    <button
                      onClick={() =>
                        onQueueContact({
                          company:
                            match.opportunity?.company ?? "",
                          name: String(contact.name || ""),
                          title: String(contact.title || ""),
                          phone: String(contact.phone || ""),
                          email: String(contact.email || ""),
                        })
                      }
                      className="px-2.5 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-xs rounded-lg transition-colors border border-emerald-500/20"
                    >
                      Queue for Outreach
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sources */}
          {research.sources_used.length > 0 && (
            <div className="px-5 py-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] text-gray-500 uppercase">
                  Sources:
                </span>
                {research.sources_used.map((src, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-[10px] text-gray-400"
                  >
                    {src}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
