"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Line, Pie, Doughnut, Scatter } from "react-chartjs-2";
import {
  fetchReport,
  downloadReportPdf,
  createShareLink,
  revokeShareLink,
  regenerateReport,
  regenerateSection,
} from "@/lib/api";
import type {
  ReportFull,
  ReportSection,
  ChartConfig,
  ReportSource,
} from "@/lib/types";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TYPE_LABELS: Record<string, string> = {
  research_report: "Research",
  market_analysis: "Market Analysis",
  property_report: "Property",
  competitive_intel: "Competitive Intel",
  due_diligence: "Due Diligence",
  custom: "Custom",
};

const POLL_INTERVAL_MS = 3000;

// ---------------------------------------------------------------------------
// Reusable: ChartRenderer
// ---------------------------------------------------------------------------

interface ChartRendererProps {
  config: ChartConfig;
}

function ChartRenderer({ config }: ChartRendererProps) {
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: { color: "#9ca3af" },
      },
      title: {
        display: !!config.title,
        text: config.title,
        color: "#e5e7eb",
        font: { size: 14, weight: "bold" as const },
      },
    },
    scales:
      config.type === "pie" || config.type === "doughnut"
        ? undefined
        : {
            x: {
              ticks: { color: "#6b7280" },
              grid: { color: "#1f2937" },
            },
            y: {
              ticks: { color: "#6b7280" },
              grid: { color: "#1f2937" },
            },
          },
    ...(config.options as Record<string, unknown>),
  };

  const chartData = {
    labels: config.data.labels,
    datasets: config.data.datasets.map((ds) => ({
      ...ds,
      backgroundColor:
        ds.backgroundColor ??
        [
          "rgba(99, 102, 241, 0.7)",
          "rgba(16, 185, 129, 0.7)",
          "rgba(245, 158, 11, 0.7)",
          "rgba(239, 68, 68, 0.7)",
          "rgba(139, 92, 246, 0.7)",
          "rgba(14, 165, 233, 0.7)",
        ],
      borderColor:
        ds.borderColor ??
        [
          "rgb(99, 102, 241)",
          "rgb(16, 185, 129)",
          "rgb(245, 158, 11)",
          "rgb(239, 68, 68)",
          "rgb(139, 92, 246)",
          "rgb(14, 165, 233)",
        ],
      borderWidth: ds.borderWidth ?? 1,
    })),
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 my-6 max-w-2xl">
      {config.type === "bar" && <Bar data={chartData} options={chartOptions} />}
      {config.type === "line" && (
        <Line data={chartData} options={chartOptions} />
      )}
      {config.type === "pie" && <Pie data={chartData} options={chartOptions} />}
      {config.type === "doughnut" && (
        <Doughnut data={chartData} options={chartOptions} />
      )}
      {config.type === "scatter" && (
        <Scatter data={chartData} options={chartOptions} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reusable: SourceCitation
// ---------------------------------------------------------------------------

function SourceCitation({
  source,
  index,
}: {
  source: ReportSource;
  index: number;
}) {
  return (
    <li className="flex items-start gap-2 text-sm">
      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center text-xs font-medium text-gray-400">
        {index + 1}
      </span>
      <div>
        {source.url ? (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-400 hover:text-indigo-300 transition-colors underline underline-offset-2"
          >
            {source.name}
          </a>
        ) : (
          <span className="text-gray-300">{source.name}</span>
        )}
        {source.type && (
          <span className="ml-2 text-xs text-gray-500">({source.type})</span>
        )}
        {source.access_date && (
          <span className="ml-2 text-xs text-gray-600">
            accessed {source.access_date}
          </span>
        )}
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Section Regeneration Modal
// ---------------------------------------------------------------------------

interface RegenModalProps {
  sectionTitle: string;
  onClose: () => void;
  onSubmit: (instructions: string) => void;
  loading: boolean;
}

function RegenModal({
  sectionTitle,
  onClose,
  onSubmit,
  loading,
}: RegenModalProps) {
  const [instructions, setInstructions] = useState("");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-gray-900 border border-gray-800 rounded-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-gray-100">
            Regenerate: {sectionTitle}
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <div className="px-6 py-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Additional instructions (optional)
          </label>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="e.g. Focus more on competitor pricing..."
            rows={4}
            className="w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors resize-none"
          />
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-800">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 font-medium rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSubmit(instructions)}
            disabled={loading}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-indigo-300 border-t-transparent rounded-full animate-spin" />
                Regenerating...
              </>
            ) : (
              "Regenerate"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Share Dialog
// ---------------------------------------------------------------------------

interface ShareDialogProps {
  url: string;
  onClose: () => void;
  onRevoke: () => void;
  revoking: boolean;
}

function ShareDialog({ url, onClose, onRevoke, revoking }: ShareDialogProps) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-gray-900 border border-gray-800 rounded-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-gray-100">Share Report</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <div className="px-6 py-4 space-y-4">
          <p className="text-sm text-gray-400">
            Anyone with this link can view the report.
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              readOnly
              value={url}
              className="flex-1 px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 font-mono truncate focus:outline-none"
            />
            <button
              onClick={handleCopy}
              className="px-3 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-800">
          <button
            onClick={onRevoke}
            disabled={revoking}
            className="px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
          >
            {revoking ? "Revoking..." : "Revoke Link"}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 font-medium rounded-lg transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Export Dropdown
// ---------------------------------------------------------------------------

interface ExportDropdownProps {
  reportId: string;
}

function ExportDropdown({ reportId }: ExportDropdownProps) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-2 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-700 transition-colors"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
        Export
        <svg
          className="w-3 h-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 8.25l-7.5 7.5-7.5-7.5"
          />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-40 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-20 overflow-hidden">
          <a
            href={`${baseUrl}/reports/${reportId}/export/csv`}
            target="_blank"
            rel="noopener noreferrer"
            className="block px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-800 transition-colors"
            onClick={() => setOpen(false)}
          >
            CSV
          </a>
          <a
            href={`${baseUrl}/reports/${reportId}/export/excel`}
            target="_blank"
            rel="noopener noreferrer"
            className="block px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-800 transition-colors border-t border-gray-800"
            onClick={() => setOpen(false)}
          >
            Excel
          </a>
          <a
            href={`${baseUrl}/reports/${reportId}/export/json`}
            target="_blank"
            rel="noopener noreferrer"
            className="block px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-800 transition-colors border-t border-gray-800"
            onClick={() => setOpen(false)}
          >
            JSON
          </a>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main: ReportDetailPage
// ---------------------------------------------------------------------------

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params.id as string;

  const [report, setReport] = useState<ReportFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeSection, setActiveSection] = useState<string>("");
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

  // Share dialog
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [sharingLoading, setSharingLoading] = useState(false);
  const [revoking, setRevoking] = useState(false);

  // Regeneration
  const [regenerating, setRegenerating] = useState(false);
  const [regenSectionIdx, setRegenSectionIdx] = useState<number | null>(null);
  const [regenLoading, setRegenLoading] = useState(false);

  // Polling ref
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Data fetching ────────────────────────────────────────────────────

  const loadReport = useCallback(async () => {
    try {
      const data = await fetchReport(reportId);
      setReport(data);
      setError(null);
      return data;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load report",
      );
      return null;
    }
  }, [reportId]);

  // Initial load
  useEffect(() => {
    setLoading(true);
    loadReport().finally(() => setLoading(false));
  }, [loadReport]);

  // Polling while generating
  useEffect(() => {
    if (report?.status === "generating") {
      pollRef.current = setInterval(async () => {
        const updated = await loadReport();
        if (updated && updated.status !== "generating" && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }, POLL_INTERVAL_MS);
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [report?.status, loadReport]);

  // ── Intersection observer for active section ─────────────────────────

  useEffect(() => {
    if (!report?.sections) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        }
      },
      { rootMargin: "-80px 0px -60% 0px", threshold: 0.1 },
    );

    const currentRefs = sectionRefs.current;
    for (const key of Object.keys(currentRefs)) {
      const el = currentRefs[key];
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [report?.sections]);

  // ── Toolbar actions ─────────────────────────────────────────────────

  function handleDownloadPdf() {
    const url = downloadReportPdf(reportId);
    window.open(url, "_blank");
  }

  function handleDownloadMarkdown() {
    if (!report?.content_markdown) return;
    const blob = new Blob([report.content_markdown], {
      type: "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.title.replace(/[^a-zA-Z0-9]/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handlePrint() {
    window.print();
  }

  async function handleShare() {
    setSharingLoading(true);
    try {
      const result = await createShareLink(reportId);
      setShareUrl(result.url);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create share link",
      );
    } finally {
      setSharingLoading(false);
    }
  }

  async function handleRevokeShare() {
    setRevoking(true);
    try {
      await revokeShareLink(reportId);
      setShareUrl(null);
      const updated = await loadReport();
      if (updated) setReport(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to revoke share link",
      );
    } finally {
      setRevoking(false);
    }
  }

  async function handleRegenerate() {
    setRegenerating(true);
    try {
      const updated = await regenerateReport(reportId);
      setReport(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to regenerate report",
      );
    } finally {
      setRegenerating(false);
    }
  }

  async function handleRegenSection(instructions: string) {
    if (regenSectionIdx === null) return;
    setRegenLoading(true);
    try {
      const updated = await regenerateSection(
        reportId,
        regenSectionIdx,
        instructions || undefined,
      );
      setReport(updated);
      setRegenSectionIdx(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to regenerate section",
      );
    } finally {
      setRegenLoading(false);
    }
  }

  // ── Scroll to section ─────────────────────────────────────────────

  function scrollToSection(sectionId: string) {
    const el = sectionRefs.current[sectionId];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  function sectionSlug(title: string, index: number): string {
    return `section-${index}-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  }

  const sections: ReportSection[] = report?.sections ?? [];
  const charts: ChartConfig[] = report?.charts ?? [];
  const sources: ReportSource[] = report?.sources ?? [];

  // Build a chart lookup by id for sections referencing chart_configs
  const sectionChartMap = new Map<number, ChartConfig[]>();
  sections.forEach((section, idx) => {
    if (section.chart_configs && section.chart_configs.length > 0) {
      sectionChartMap.set(idx, section.chart_configs);
    }
  });

  // Charts not assigned to a specific section
  const globalCharts = charts.filter(
    (chart) =>
      !Array.from(sectionChartMap.values())
        .flat()
        .some((sc) => sc.id === chart.id),
  );

  // ── Loading state ───────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-4">Loading report...</p>
        </div>
      </div>
    );
  }

  // ── Error state ─────────────────────────────────────────────────────

  if (error && !report) {
    return (
      <div className="max-w-2xl mx-auto mt-16">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center">
          <svg
            className="w-10 h-10 mx-auto text-red-400 mb-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          <p className="text-sm text-red-400 mb-4">{error}</p>
          <button
            onClick={() => router.push("/reports")}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 font-medium rounded-lg transition-colors"
          >
            Back to Reports
          </button>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const typeLabel =
    TYPE_LABELS[report.report_type] ?? report.report_type;

  // ── Generating state ────────────────────────────────────────────────

  if (report.status === "generating") {
    return (
      <div className="max-w-2xl mx-auto mt-16">
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-8 text-center">
          <div className="inline-block w-10 h-10 border-2 border-amber-400/40 border-t-amber-400 rounded-full animate-spin mb-4" />
          <h2 className="text-lg font-semibold text-gray-100 mb-2">
            {report.title}
          </h2>
          <p className="text-sm text-amber-400 mb-1">
            Report is being generated...
          </p>
          <p className="text-xs text-gray-500">
            This page will update automatically when ready.
          </p>
        </div>
      </div>
    );
  }

  // ── Failed state ────────────────────────────────────────────────────

  if (report.status === "failed") {
    return (
      <div className="max-w-2xl mx-auto mt-16">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-8 text-center">
          <svg
            className="w-10 h-10 mx-auto text-red-400 mb-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          <h2 className="text-lg font-semibold text-gray-100 mb-2">
            {report.title}
          </h2>
          <p className="text-sm text-red-400 mb-4">
            Report generation failed.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => router.push("/reports")}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 font-medium rounded-lg transition-colors"
            >
              Back to Reports
            </button>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {regenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-indigo-300 border-t-transparent rounded-full animate-spin" />
                  Regenerating...
                </>
              ) : (
                "Retry"
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Ready state: full report viewer ─────────────────────────────────

  return (
    <div className="flex min-h-screen">
      {/* ── Left sidebar: Table of Contents ──────────────────────────── */}
      <aside
        className={`fixed top-0 left-64 h-screen bg-gray-950 border-r border-gray-800 transition-all duration-200 z-30 print:hidden ${
          sidebarOpen ? "w-64" : "w-0 overflow-hidden"
        }`}
      >
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-800">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Contents
          </h3>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1 rounded text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5"
              />
            </svg>
          </button>
        </div>
        <nav className="px-3 py-4 space-y-0.5 overflow-y-auto max-h-[calc(100vh-56px)]">
          {report.executive_summary && (
            <button
              onClick={() => scrollToSection("executive-summary")}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                activeSection === "executive-summary"
                  ? "bg-indigo-500/10 text-indigo-400"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/60"
              }`}
            >
              Executive Summary
            </button>
          )}
          {sections.map((section, idx) => {
            const slug = sectionSlug(section.title, idx);
            return (
              <button
                key={slug}
                onClick={() => scrollToSection(slug)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeSection === slug
                    ? "bg-indigo-500/10 text-indigo-400"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/60"
                }`}
              >
                {section.title}
              </button>
            );
          })}
          {report.methodology && (
            <button
              onClick={() => scrollToSection("methodology")}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                activeSection === "methodology"
                  ? "bg-indigo-500/10 text-indigo-400"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/60"
              }`}
            >
              Methodology
            </button>
          )}
          {sources.length > 0 && (
            <button
              onClick={() => scrollToSection("sources")}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                activeSection === "sources"
                  ? "bg-indigo-500/10 text-indigo-400"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/60"
              }`}
            >
              Sources ({sources.length})
            </button>
          )}
        </nav>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main
        className={`flex-1 transition-all duration-200 ${
          sidebarOpen ? "ml-64" : "ml-0"
        }`}
      >
        {/* ── Toolbar ──────────────────────────────────────────────── */}
        <div className="sticky top-0 z-20 bg-gray-950/95 backdrop-blur-sm border-b border-gray-800 print:hidden">
          <div className="max-w-4xl mx-auto px-6 py-3 flex items-center gap-2 flex-wrap">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors mr-2"
                title="Show table of contents"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                  />
                </svg>
              </button>
            )}

            <button
              onClick={handleDownloadPdf}
              className="flex items-center gap-2 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-700 transition-colors"
              title="Download PDF"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
              PDF
            </button>

            <button
              onClick={handleDownloadMarkdown}
              disabled={!report.content_markdown}
              className="flex items-center gap-2 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              title="Download Markdown"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
              MD
            </button>

            <ExportDropdown reportId={reportId} />

            <button
              onClick={handleShare}
              disabled={sharingLoading}
              className="flex items-center gap-2 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-50"
              title="Share report"
            >
              {sharingLoading ? (
                <div className="w-4 h-4 border-[1.5px] border-gray-400 border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z"
                  />
                </svg>
              )}
              Share
            </button>

            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:bg-gray-700 transition-colors"
              title="Print report"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0110.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0l.229 2.523a1.125 1.125 0 01-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0021 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 00-1.913-.247M6.34 18H5.25A2.25 2.25 0 013 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.041 48.041 0 011.913-.247m0 0a48.579 48.579 0 0110.498 0m-10.498 0v-.39c0-1.18.91-2.164 2.09-2.201a51.964 51.964 0 013.32 0c1.18.037 2.09 1.022 2.09 2.201v.39"
                />
              </svg>
              Print
            </button>

            <div className="flex-1" />

            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {regenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-indigo-300 border-t-transparent rounded-full animate-spin" />
                  Regenerating...
                </>
              ) : (
                <>
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
                    />
                  </svg>
                  Regenerate
                </>
              )}
            </button>
          </div>
        </div>

        {/* ── Error banner ─────────────────────────────────────────── */}
        {error && (
          <div className="max-w-4xl mx-auto px-6 mt-4">
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          </div>
        )}

        {/* ── Report content ───────────────────────────────────────── */}
        <article className="max-w-4xl mx-auto px-6 py-8">
          {/* Title block */}
          <header className="mb-10">
            <div className="flex items-center gap-3 mb-3">
              <span className="inline-flex items-center px-2.5 py-1 rounded-md border text-xs font-medium bg-indigo-500/10 text-indigo-400 border-indigo-500/20">
                {typeLabel}
              </span>
              <span className="inline-flex items-center px-2.5 py-1 rounded-md border text-xs font-medium bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                Ready
              </span>
              {report.share_enabled && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border text-xs font-medium bg-blue-500/10 text-blue-400 border-blue-500/20">
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"
                    />
                  </svg>
                  Shared
                </span>
              )}
            </div>
            <h1 className="text-3xl font-bold text-gray-100 mb-3">
              {report.title}
            </h1>
            {report.description && (
              <p className="text-base text-gray-400">{report.description}</p>
            )}
            <div className="flex items-center gap-4 mt-4 text-xs text-gray-500">
              <span>
                Created{" "}
                {new Date(report.created_at).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
              {report.updated_at !== report.created_at && (
                <span>
                  Updated{" "}
                  {new Date(report.updated_at).toLocaleDateString("en-US", {
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
                </span>
              )}
            </div>
          </header>

          {/* Executive Summary */}
          {report.executive_summary && (
            <section
              id="executive-summary"
              ref={(el) => {
                sectionRefs.current["executive-summary"] = el;
              }}
              className="mb-10 scroll-mt-20"
            >
              <h2 className="text-xl font-bold text-gray-100 mb-4 pb-2 border-b border-gray-800">
                Executive Summary
              </h2>
              <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-xl p-6">
                <div className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-headings:text-gray-100 prose-strong:text-gray-200 prose-a:text-indigo-400">
                  <ReactMarkdown>{report.executive_summary}</ReactMarkdown>
                </div>
              </div>
            </section>
          )}

          {/* Sections */}
          {sections
            .sort((a, b) => a.order - b.order)
            .map((section, idx) => {
              const slug = sectionSlug(section.title, idx);
              const sectionCharts = sectionChartMap.get(idx) ?? [];

              return (
                <section
                  key={slug}
                  id={slug}
                  ref={(el) => {
                    sectionRefs.current[slug] = el;
                  }}
                  className="mb-10 scroll-mt-20 group/section"
                >
                  <div className="flex items-center gap-3 mb-4 pb-2 border-b border-gray-800">
                    <h2 className="text-xl font-bold text-gray-100 flex-1">
                      {section.title}
                    </h2>
                    <button
                      onClick={() => setRegenSectionIdx(idx)}
                      className="opacity-0 group-hover/section:opacity-100 p-1.5 rounded-lg text-gray-500 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all"
                      title="Regenerate this section"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
                        />
                      </svg>
                    </button>
                  </div>

                  <div className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-headings:text-gray-100 prose-strong:text-gray-200 prose-a:text-indigo-400 prose-li:text-gray-300 prose-code:text-indigo-300 prose-code:bg-gray-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-800 prose-pre:border prose-pre:border-gray-700 prose-blockquote:border-indigo-500/40 prose-blockquote:text-gray-400 prose-table:text-gray-300 prose-th:text-gray-200 prose-td:border-gray-700 prose-th:border-gray-700">
                    <ReactMarkdown>{section.content_md}</ReactMarkdown>
                  </div>

                  {/* Section-specific charts */}
                  {sectionCharts.map((chart) => (
                    <ChartRenderer key={chart.id} config={chart} />
                  ))}
                </section>
              );
            })}

          {/* Global charts (not tied to a section) */}
          {globalCharts.length > 0 && (
            <section className="mb-10">
              <h2 className="text-xl font-bold text-gray-100 mb-4 pb-2 border-b border-gray-800">
                Charts
              </h2>
              <div className="space-y-6">
                {globalCharts.map((chart) => (
                  <ChartRenderer key={chart.id} config={chart} />
                ))}
              </div>
            </section>
          )}

          {/* Methodology */}
          {report.methodology && (
            <section
              id="methodology"
              ref={(el) => {
                sectionRefs.current["methodology"] = el;
              }}
              className="mb-10 scroll-mt-20"
            >
              <h2 className="text-xl font-bold text-gray-100 mb-4 pb-2 border-b border-gray-800">
                Methodology
              </h2>
              <div className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-headings:text-gray-100 prose-strong:text-gray-200 prose-a:text-indigo-400">
                <ReactMarkdown>{report.methodology}</ReactMarkdown>
              </div>
            </section>
          )}

          {/* Sources */}
          {sources.length > 0 && (
            <section
              id="sources"
              ref={(el) => {
                sectionRefs.current["sources"] = el;
              }}
              className="mb-10 scroll-mt-20"
            >
              <h2 className="text-xl font-bold text-gray-100 mb-4 pb-2 border-b border-gray-800">
                Sources
              </h2>
              <ol className="space-y-3">
                {sources.map((source, idx) => (
                  <SourceCitation
                    key={`${source.name}-${idx}`}
                    source={source}
                    index={idx}
                  />
                ))}
              </ol>
            </section>
          )}
        </article>
      </main>

      {/* ── Share Dialog ───────────────────────────────────────────── */}
      {shareUrl && (
        <ShareDialog
          url={shareUrl}
          onClose={() => setShareUrl(null)}
          onRevoke={handleRevokeShare}
          revoking={revoking}
        />
      )}

      {/* ── Section Regeneration Modal ─────────────────────────────── */}
      {regenSectionIdx !== null && sections[regenSectionIdx] && (
        <RegenModal
          sectionTitle={sections[regenSectionIdx].title}
          onClose={() => setRegenSectionIdx(null)}
          onSubmit={handleRegenSection}
          loading={regenLoading}
        />
      )}
    </div>
  );
}
