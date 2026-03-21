"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

// ── Types ────────────────────────────────────────────────────────────

interface VoiceExtraction {
  id: string;
  name: string;
  status: "draft" | "active" | "paused" | "completed";
  objective: string;
  persona_name: string | null;
  total_targets: number;
  calls_completed: number;
  successful_calls: number;
  data_points_extracted: number;
  created_at: string;
  updated_at: string;
}

interface VoiceExtractionListResponse {
  items: VoiceExtraction[];
  total: number;
}

// ── Constants ────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  active: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  paused: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function computeSuccessRate(extraction: VoiceExtraction): string {
  if (extraction.calls_completed === 0) return "0%";
  const rate = (extraction.successful_calls / extraction.calls_completed) * 100;
  return `${Math.round(rate)}%`;
}

function computeProgress(extraction: VoiceExtraction): number {
  if (extraction.total_targets === 0) return 0;
  return Math.min(
    100,
    Math.round((extraction.calls_completed / extraction.total_targets) * 100),
  );
}

// ── Component ────────────────────────────────────────────────────────

export default function VoiceExtractionsPage() {
  const [extractions, setExtractions] = useState<VoiceExtraction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/voice/sessions", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "Unknown error");
        throw new Error(`API ${res.status}: ${body}`);
      }
      const data: VoiceExtractionListResponse = await res.json();
      setExtractions(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch extractions",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">
            Voice Extractions
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage voice extraction campaigns and track progress
          </p>
        </div>
        <Link
          href="/voice/extractions/new"
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 4.5v15m7.5-7.5h-15"
            />
          </svg>
          New Extraction
        </Link>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Summary */}
      {!loading && (
        <p className="text-xs text-gray-500 mb-4">
          Showing {extractions.length} of {total} extractions
        </p>
      )}

      {/* Loading */}
      {loading ? (
        <div className="text-center py-16">
          <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-3">
            Loading extractions...
          </p>
        </div>
      ) : extractions.length === 0 ? (
        /* Empty State */
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <svg
            className="w-12 h-12 mx-auto text-gray-700 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z"
            />
          </svg>
          <p className="text-sm text-gray-400 mb-2">No extractions yet.</p>
          <p className="text-xs text-gray-600 mb-4">
            Create your first voice extraction campaign to get started.
          </p>
          <Link
            href="/voice/extractions/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4.5v15m7.5-7.5h-15"
              />
            </svg>
            New Extraction
          </Link>
        </div>
      ) : (
        /* Table */
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Progress
                  </th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Targets
                  </th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Calls Completed
                  </th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Success Rate
                  </th>
                  <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Data Points
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {extractions.map((extraction) => {
                  const statusStyle =
                    STATUS_STYLES[extraction.status] ?? STATUS_STYLES.draft;
                  const progress = computeProgress(extraction);
                  const successRate = computeSuccessRate(extraction);

                  return (
                    <tr
                      key={extraction.id}
                      className="hover:bg-gray-800/40 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <Link
                          href={`/voice/extractions/${extraction.id}`}
                          className="text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
                        >
                          {extraction.name}
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium capitalize ${statusStyle}`}
                        >
                          {extraction.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 min-w-[140px]">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                extraction.status === "completed"
                                  ? "bg-emerald-500"
                                  : "bg-indigo-500"
                              }`}
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500 w-8 text-right">
                            {progress}%
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-sm text-gray-300">
                          {extraction.total_targets}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-sm text-gray-300">
                          {extraction.calls_completed}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-sm text-gray-300">
                          {successRate}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-sm text-gray-300">
                          {extraction.data_points_extracted}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">
                          {formatDate(extraction.created_at)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
