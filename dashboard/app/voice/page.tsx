"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchVoiceExtractions } from "@/lib/api";
import type { VoiceExtraction } from "@/lib/types";

interface VoiceTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  fields: string[];
}

const BUILT_IN_TEMPLATES: VoiceTemplate[] = [
  {
    id: "t1",
    name: "Market Research Survey",
    description: "Gather market insights through structured phone interviews",
    category: "Research",
    fields: ["company_name", "industry", "pain_points", "budget_range", "decision_timeline"],
  },
  {
    id: "t2",
    name: "Customer Feedback",
    description: "Collect product feedback and satisfaction ratings from customers",
    category: "Feedback",
    fields: ["satisfaction_score", "feature_requests", "nps_rating", "churn_risk"],
  },
  {
    id: "t3",
    name: "Lead Qualification",
    description: "Qualify inbound leads with automated screening calls",
    category: "Sales",
    fields: ["company_size", "budget", "timeline", "decision_maker", "use_case"],
  },
  {
    id: "t4",
    name: "Property Verification",
    description: "Verify property details and availability through owner calls",
    category: "Real Estate",
    fields: ["availability", "asking_price", "property_condition", "motivated_seller"],
  },
  {
    id: "t5",
    name: "Vendor Assessment",
    description: "Screen and assess potential vendors via structured interviews",
    category: "Procurement",
    fields: ["capabilities", "pricing_model", "references", "compliance", "capacity"],
  },
  {
    id: "t6",
    name: "Event RSVP & Info",
    description: "Confirm attendance and gather dietary or accessibility needs",
    category: "Events",
    fields: ["attendance_status", "guest_count", "dietary_restrictions", "accessibility_needs"],
  },
];

const EXTRACTION_STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  running: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  completed: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  paused: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  failed: "bg-red-500/10 text-red-400 border border-red-500/20",
  draft: "bg-gray-700/50 text-gray-300",
};

const CATEGORY_STYLES: Record<string, string> = {
  Research: "bg-purple-500/10 text-purple-400",
  Feedback: "bg-blue-500/10 text-blue-400",
  Sales: "bg-emerald-500/10 text-emerald-400",
  "Real Estate": "bg-amber-500/10 text-amber-400",
  Procurement: "bg-cyan-500/10 text-cyan-400",
  Events: "bg-pink-500/10 text-pink-400",
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function VoicePage() {
  const [extractions, setExtractions] = useState<VoiceExtraction[]>([]);
  const [loadingExtractions, setLoadingExtractions] = useState(true);
  const [extractionError, setExtractionError] = useState<string | null>(null);

  useEffect(() => {
    loadExtractions();
  }, []);

  async function loadExtractions() {
    try {
      setLoadingExtractions(true);
      setExtractionError(null);
      const data = await fetchVoiceExtractions({});
      setExtractions(data);
    } catch (err) {
      setExtractionError(
        err instanceof Error ? err.message : "Failed to load extractions"
      );
    } finally {
      setLoadingExtractions(false);
    }
  }

  function getProgress(ext: VoiceExtraction): number {
    if (ext.total_targets === 0) return 0;
    return Math.round((ext.calls_completed / ext.total_targets) * 100);
  }

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold text-gray-100">
          Voice Extractions
        </h1>
        <Link
          href="/voice/extractions"
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          New Extraction
        </Link>
      </div>

      {/* Extraction Sessions Section */}
      <section className="mb-12">
        <h2 className="text-lg font-medium text-gray-200 mb-4">
          Extraction Sessions
        </h2>

        {extractionError && (
          <div className="mb-4 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {extractionError}
          </div>
        )}

        {loadingExtractions ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-gray-900 border border-gray-800/50 rounded-xl p-5 animate-pulse"
              >
                <div className="h-5 bg-gray-800 rounded w-3/4 mb-3" />
                <div className="h-4 bg-gray-800 rounded w-1/2 mb-4" />
                <div className="h-2 bg-gray-800 rounded w-full" />
              </div>
            ))}
          </div>
        ) : extractions.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-12 text-center">
            <div className="text-gray-500 mb-2 text-3xl">&#127908;</div>
            <p className="text-gray-400 font-medium">
              No extraction sessions yet.
            </p>
            <p className="text-gray-500 text-sm mt-1">
              Start a new voice extraction to collect data via phone calls.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {extractions.map((ext) => {
              const progress = getProgress(ext);
              return (
                <Link
                  key={ext.id}
                  href={`/voice/extractions/${ext.id}`}
                  className="bg-gray-900 border border-gray-800/50 rounded-xl p-5 hover:border-gray-700/60 transition-colors block"
                >
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-gray-100 font-medium truncate pr-2">
                      {ext.name}
                    </h3>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${EXTRACTION_STATUS_STYLES[ext.status] ?? EXTRACTION_STATUS_STYLES.draft}`}
                    >
                      {ext.status}
                    </span>
                  </div>

                  <div className="mb-3">
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                      <span>Progress</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>
                      {ext.calls_completed}/{ext.total_targets} calls
                    </span>
                    <span>{formatDate(ext.created_at)}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      {/* Templates Section */}
      <section>
        <h2 className="text-lg font-medium text-gray-200 mb-4">Templates</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {BUILT_IN_TEMPLATES.map((tpl) => (
            <div
              key={tpl.id}
              className="bg-gray-900 border border-gray-800/50 rounded-xl p-5 hover:border-gray-700/60 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-100 font-medium">{tpl.name}</h3>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${CATEGORY_STYLES[tpl.category] ?? "bg-gray-700/50 text-gray-400"}`}
                >
                  {tpl.category}
                </span>
              </div>
              <p className="text-gray-500 text-sm mb-3">{tpl.description}</p>
              <p className="text-xs text-gray-600">
                {tpl.fields.length} field{tpl.fields.length !== 1 ? "s" : ""}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
