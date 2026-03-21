"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchReports,
  createReport,
  deleteReport,
  downloadReportPdf,
  createShareLink,
} from "@/lib/api";
import type { Report } from "@/lib/types";

const TYPE_STYLES: Record<string, string> = {
  research_report: "bg-emerald-500/10 text-emerald-400",
  market_analysis: "bg-blue-500/10 text-blue-400",
  property_report: "bg-amber-500/10 text-amber-400",
  competitive_intel: "bg-purple-500/10 text-purple-400",
  due_diligence: "bg-cyan-500/10 text-cyan-400",
  custom: "bg-gray-700/50 text-gray-400",
};

const TYPE_LABELS: Record<string, string> = {
  research_report: "Research",
  market_analysis: "Market Analysis",
  property_report: "Property",
  competitive_intel: "Competitive Intel",
  due_diligence: "Due Diligence",
  custom: "Custom",
};

const STATUS_STYLES: Record<string, string> = {
  generating: "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse",
  ready: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  failed: "bg-red-500/10 text-red-400 border border-red-500/20",
};

const REPORT_TYPES = [
  { value: "research_report", label: "Research Report" },
  { value: "market_analysis", label: "Market Analysis" },
  { value: "property_report", label: "Property Report" },
  { value: "competitive_intel", label: "Competitive Intel" },
  { value: "due_diligence", label: "Due Diligence" },
  { value: "custom", label: "Custom" },
];

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [formMissionId, setFormMissionId] = useState("");
  const [formReportType, setFormReportType] = useState("research_report");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  async function loadReports() {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchReports({});
      setReports(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!formMissionId.trim()) return;
    try {
      setCreating(true);
      await createReport({
        mission_id: formMissionId.trim(),
        report_type: formReportType,
      });
      setShowModal(false);
      setFormMissionId("");
      setFormReportType("research_report");
      await loadReports();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create report");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string, title: string) {
    if (!confirm(`Delete report "${title}"? This cannot be undone.`)) return;
    try {
      await deleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete report");
    }
  }

  async function handleShare(id: string) {
    try {
      const res = await createShareLink(id);
      await navigator.clipboard.writeText(res.url);
      alert("Share link copied to clipboard.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create share link");
    }
  }

  function handleDownload(id: string) {
    const url = downloadReportPdf(id);
    window.open(url, "_blank");
  }

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold text-gray-100">Reports</h1>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Generate Report
        </button>
      </div>

      {error && (
        <div className="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-gray-900 border border-gray-800/50 rounded-xl p-5 animate-pulse"
            >
              <div className="h-5 bg-gray-800 rounded w-3/4 mb-3" />
              <div className="h-4 bg-gray-800 rounded w-1/2 mb-4" />
              <div className="h-3 bg-gray-800 rounded w-full" />
            </div>
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-16 text-center">
          <div className="text-gray-500 mb-2 text-4xl">&#128196;</div>
          <p className="text-gray-400 font-medium">No reports yet.</p>
          <p className="text-gray-500 text-sm mt-1">
            Run a mission first, then generate a report.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="inline-block mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Generate Report
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reports.map((report) => (
            <div
              key={report.id}
              className="bg-gray-900 border border-gray-800/50 rounded-xl p-5 flex flex-col justify-between hover:border-gray-700/60 transition-colors"
            >
              <div>
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-gray-100 font-medium truncate pr-2">
                    {report.title}
                  </h3>
                </div>

                <div className="flex items-center gap-2 mb-3">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${TYPE_STYLES[report.report_type] ?? TYPE_STYLES.custom}`}
                  >
                    {TYPE_LABELS[report.report_type] ?? report.report_type}
                  </span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLES[report.status] ?? STATUS_STYLES.ready}`}
                  >
                    {report.status}
                  </span>
                </div>

                <p className="text-xs text-gray-500">
                  Created {formatDate(report.created_at)}
                </p>
              </div>

              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-800/50 flex-wrap">
                <Link
                  href={`/reports/${report.id}`}
                  className="px-3 py-1.5 text-xs font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-md transition-colors"
                >
                  View
                </Link>
                <button
                  onClick={() => handleDownload(report.id)}
                  className="px-3 py-1.5 text-xs font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 rounded-md transition-colors"
                >
                  PDF
                </button>
                <button
                  onClick={() => handleShare(report.id)}
                  className="px-3 py-1.5 text-xs font-medium text-purple-400 bg-purple-500/10 hover:bg-purple-500/20 rounded-md transition-colors"
                >
                  Share
                </button>
                <button
                  onClick={() => handleDelete(report.id, report.title)}
                  className="px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/10 rounded-md transition-colors ml-auto"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Generate Report Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setShowModal(false)}
          />
          <div className="relative bg-gray-900 border border-gray-800/50 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">
              Generate Report
            </h2>

            <label className="block mb-4">
              <span className="text-sm text-gray-400 mb-1 block">
                Mission ID
              </span>
              <input
                type="text"
                value={formMissionId}
                onChange={(e) => setFormMissionId(e.target.value)}
                placeholder="Enter mission ID"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 text-sm placeholder:text-gray-600 focus:outline-none focus:border-emerald-500/50"
              />
            </label>

            <label className="block mb-6">
              <span className="text-sm text-gray-400 mb-1 block">
                Report Type
              </span>
              <select
                value={formReportType}
                onChange={(e) => setFormReportType(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 text-sm focus:outline-none focus:border-emerald-500/50"
              >
                {REPORT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !formMissionId.trim()}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {creating ? "Generating..." : "Generate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
