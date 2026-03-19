"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchOpportunity } from "@/lib/api";
import type { Opportunity } from "@/lib/types";

export default function OpportunityDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const opp = await fetchOpportunity(id);
        setOpportunity(opp);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to fetch opportunity"
        );
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-4xl">
        <div className="text-center py-16">
          <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading opportunity...</p>
        </div>
      </div>
    );
  }

  if (error || !opportunity) {
    return (
      <div className="max-w-4xl">
        <Link
          href="/opportunities"
          className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors mb-6"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Back to Opportunities
        </Link>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error ?? "Opportunity not found"}</p>
        </div>
      </div>
    );
  }

  const SOURCE_COLORS: Record<string, string> = {
    greenhouse: "bg-green-500/10 text-green-400 border-green-500/20",
    lever: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    yc_hn: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  };

  const sourceColor =
    SOURCE_COLORS[opportunity.source] ??
    "bg-gray-500/10 text-gray-400 border-gray-500/20";

  return (
    <div className="max-w-4xl">
      <Link
        href="/opportunities"
        className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to Opportunities
      </Link>

      {/* Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">
              {opportunity.title}
            </h1>
            <p className="text-base text-gray-400 mt-1">
              {opportunity.company}
            </p>
          </div>
          <span
            className={`shrink-0 inline-flex items-center px-2.5 py-1 rounded-md border text-xs font-medium ${sourceColor}`}
          >
            {opportunity.source}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400">
          {opportunity.location && (
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 0115 0z" />
              </svg>
              {opportunity.location}
            </span>
          )}
          <span className="flex items-center gap-1.5 text-gray-500">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
            </svg>
            {new Date(opportunity.created_at).toLocaleDateString()}
          </span>
        </div>

        {opportunity.url && (
          <a
            href={opportunity.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 mt-4 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
            Apply Now
          </a>
        )}
      </div>

      {/* Description */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
          Job Description
        </h2>
        {opportunity.description ? (
          <div className="prose prose-sm prose-invert max-w-none">
            {opportunity.description.split("\n").map((paragraph, idx) => {
              if (paragraph.trim() === "") return <br key={idx} />;
              return (
                <p key={idx} className="text-sm text-gray-400 leading-relaxed mb-3">
                  {paragraph}
                </p>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No description available.</p>
        )}
      </div>

      {/* Metadata */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mt-6">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
          Details
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <Detail label="Source" value={opportunity.source} />
          <Detail label="Source ID" value={opportunity.source_id} />
          <Detail label="Company" value={opportunity.company} />
          <Detail label="Location" value={opportunity.location ?? "Not specified"} />
          <Detail
            label="Posted"
            value={new Date(opportunity.created_at).toLocaleString()}
          />
          <Detail label="ID" value={opportunity.id} />
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-gray-500 uppercase tracking-wider">
        {label}
      </span>
      <p className="text-sm text-gray-300 mt-0.5 break-all">{value}</p>
    </div>
  );
}
