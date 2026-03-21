"use client";

import { cn } from "@/lib/cn";
import Spinner from "@/components/ui/Spinner";
import type { Contact, Match } from "@/lib/types";

const SOURCE_COLORS: Record<string, string> = {
  exa: "bg-purple-500/15 text-purple-400 border-purple-500/25",
  openclaw: "bg-blue-500/15 text-blue-400 border-blue-500/25",
  manual: "bg-gray-500/15 text-gray-400 border-gray-500/25",
};

interface CompanyGroupProps {
  company: string;
  contacts: Contact[];
  companyMatch: Match | undefined;
  researchLoading: boolean;
  onResearch: (matchId: string) => void;
  onRemoveContact: (id: string) => void;
}

export default function CompanyGroup({
  company,
  contacts,
  companyMatch,
  researchLoading,
  onResearch,
  onRemoveContact,
}: CompanyGroupProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800 bg-gray-900/80">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center">
            <span className="text-xs font-bold text-indigo-400">
              {company.charAt(0).toUpperCase()}
            </span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-200">{company}</h3>
            <p className="text-[10px] text-gray-500">
              {contacts.length} contact{contacts.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        {companyMatch && (
          <button
            onClick={() => onResearch(companyMatch.id)}
            disabled={researchLoading}
            className={cn(
              "px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400",
              "text-xs font-medium rounded-lg transition-colors",
              "flex items-center gap-1.5 disabled:opacity-50",
              "border border-purple-500/20",
            )}
          >
            {researchLoading ? (
              <>
                <Spinner size="sm" />
                Researching...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                </svg>
                Research {company}
              </>
            )}
          </button>
        )}
      </div>

      <div className="divide-y divide-gray-800/50">
        {contacts.map((c) => (
          <div
            key={c.id}
            className="px-5 py-3 flex items-center justify-between hover:bg-gray-800/30 transition-colors duration-150"
          >
            <div className="flex items-center gap-4 min-w-0">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-100 truncate">
                    {c.name || "Unnamed"}
                  </span>
                  {c.title && (
                    <span className="text-xs text-gray-500 truncate">
                      {c.title}
                    </span>
                  )}
                  <span
                    className={cn(
                      "px-1.5 py-0.5 rounded text-[9px] font-medium uppercase border",
                      SOURCE_COLORS[c.source] ?? SOURCE_COLORS.manual,
                    )}
                  >
                    {c.source}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  {c.phone && (
                    <span className="text-xs text-gray-500 font-mono">
                      {c.phone}
                    </span>
                  )}
                  {c.email && (
                    <span className="text-xs text-gray-500">{c.email}</span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={() => onRemoveContact(c.id)}
              className="text-xs text-red-400/40 hover:text-red-400 transition-colors shrink-0 ml-4"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
