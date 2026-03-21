"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { fetchSharedReport } from "@/lib/api";
import type { ReportFull, ReportSection, ChartConfig, ReportSource } from "@/lib/types";
import Spinner from "@/components/ui/Spinner";
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
import { Bar, Line, Pie, Scatter, Doughnut } from "react-chartjs-2";

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

// ── Chart renderer ───────────────────────────────────────────────────

function ReportChart({ config }: { config: ChartConfig }) {
  const baseOptions = {
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
    scales: {
      x: {
        ticks: { color: "#6b7280" },
        grid: { color: "#1f2937" },
      },
      y: {
        ticks: { color: "#6b7280" },
        grid: { color: "#1f2937" },
      },
    },
    ...((config.options ?? {}) as Record<string, unknown>),
  };

  const noAxesOptions = {
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
    ...((config.options ?? {}) as Record<string, unknown>),
  };

  switch (config.type) {
    case "bar":
      return <Bar data={config.data} options={baseOptions} />;
    case "line":
      return <Line data={config.data} options={baseOptions} />;
    case "pie":
      return <Pie data={config.data} options={noAxesOptions} />;
    case "doughnut":
      return <Doughnut data={config.data} options={noAxesOptions} />;
    case "scatter":
      return <Scatter data={config.data} options={baseOptions} />;
    default:
      return <Bar data={config.data} options={baseOptions} />;
  }
}

// ── Markdown-ish renderer (simple) ───────────────────────────────────

function MarkdownContent({ markdown }: { markdown: string }) {
  const lines = markdown.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];
  let listType: "ul" | "ol" | null = null;

  function flushList() {
    if (listItems.length > 0 && listType) {
      const Tag = listType;
      elements.push(
        <Tag
          key={`list-${elements.length}`}
          className={`${listType === "ol" ? "list-decimal" : "list-disc"} list-inside space-y-1 text-gray-300 text-sm leading-relaxed my-2`}
        >
          {listItems.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </Tag>,
      );
      listItems = [];
      listType = null;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Headings
    const headingMatch = line.match(/^(#{1,4})\s+(.*)/);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length;
      const text = headingMatch[2];
      const headingClasses: Record<number, string> = {
        1: "text-2xl font-bold text-gray-100 mt-6 mb-3",
        2: "text-xl font-semibold text-gray-100 mt-5 mb-2",
        3: "text-lg font-semibold text-gray-200 mt-4 mb-2",
        4: "text-base font-medium text-gray-300 mt-3 mb-1",
      };
      elements.push(
        <p key={i} className={headingClasses[level] ?? headingClasses[4]}>
          {text}
        </p>,
      );
      continue;
    }

    // Unordered list
    const ulMatch = line.match(/^[-*+]\s+(.*)/);
    if (ulMatch) {
      if (listType === "ol") flushList();
      listType = "ul";
      listItems.push(ulMatch[1]);
      continue;
    }

    // Ordered list
    const olMatch = line.match(/^\d+\.\s+(.*)/);
    if (olMatch) {
      if (listType === "ul") flushList();
      listType = "ol";
      listItems.push(olMatch[1]);
      continue;
    }

    flushList();

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={i} className="border-gray-800 my-4" />);
      continue;
    }

    // Blank line
    if (line.trim() === "") {
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      elements.push(
        <blockquote
          key={i}
          className="border-l-2 border-indigo-500/40 pl-4 py-1 text-sm text-gray-400 italic my-2"
        >
          {line.slice(2)}
        </blockquote>,
      );
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={i} className="text-sm text-gray-300 leading-relaxed my-1.5">
        {renderInlineMarkdown(line)}
      </p>,
    );
  }

  flushList();

  return <>{elements}</>;
}

function renderInlineMarkdown(text: string): React.ReactNode {
  // Bold
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-gray-200">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

// ── Section renderer ─────────────────────────────────────────────────

function SectionView({ section }: { section: ReportSection }) {
  return (
    <div className="mb-8">
      <h2 className="text-xl font-semibold text-gray-100 mb-3 pb-2 border-b border-gray-800">
        {section.title}
      </h2>
      <MarkdownContent markdown={section.content_md} />
      {section.chart_configs && section.chart_configs.length > 0 && (
        <div className="mt-4 grid gap-6 sm:grid-cols-1 lg:grid-cols-2">
          {section.chart_configs.map((chart) => (
            <div
              key={chart.id}
              className="bg-gray-800/40 border border-gray-800 rounded-xl p-4"
            >
              <ReportChart config={chart} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Sources list ─────────────────────────────────────────────────────

function SourcesList({ sources }: { sources: ReportSource[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-8 pt-6 border-t border-gray-800">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">Sources</h2>
      <ol className="space-y-2 list-decimal list-inside">
        {sources.map((src, idx) => (
          <li key={idx} className="text-sm text-gray-400">
            <span className="text-gray-300 font-medium">{src.name}</span>
            {src.type && (
              <span className="ml-2 text-xs text-gray-500">({src.type})</span>
            )}
            {src.url && (
              <>
                {" - "}
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 break-all"
                >
                  {src.url}
                </a>
              </>
            )}
            {src.access_date && (
              <span className="ml-2 text-xs text-gray-600">
                (accessed {src.access_date})
              </span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

// ── Error state ──────────────────────────────────────────────────────

function ErrorView({ message }: { message: string }) {
  const isNotFound = message.toLowerCase().includes("not found");

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-500/10 mb-4">
          <svg
            className="w-8 h-8 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            {isNotFound ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
              />
            )}
          </svg>
        </div>
        <h1 className="text-xl font-semibold text-gray-100 mb-2">
          {isNotFound ? "Report Not Found" : "Unable to Load Report"}
        </h1>
        <p className="text-sm text-gray-400">
          {isNotFound
            ? "This shared report link may have expired or been revoked."
            : message}
        </p>
      </div>
    </div>
  );
}

// ── Loading state ────────────────────────────────────────────────────

function LoadingView() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <Spinner size="lg" className="mx-auto" />
        <p className="mt-4 text-sm text-gray-400">Loading report...</p>
      </div>
    </div>
  );
}

// ── Footer ───────────────────────────────────────────────────────────

function SharedFooter() {
  return (
    <footer className="border-t border-gray-800 mt-12 py-6 text-center">
      <p className="text-xs text-gray-600">
        Powered by{" "}
        <span className="text-gray-400 font-medium">Agentary</span>
      </p>
    </footer>
  );
}

// ── Main page ────────────────────────────────────────────────────────

export default function SharedReportPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const [report, setReport] = useState<ReportFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchSharedReport(token)
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  if (loading) return <LoadingView />;
  if (error) return <ErrorView message={error} />;
  if (!report) return <ErrorView message="Report not found" />;

  const reportTypeLabel =
    report.report_type
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* ── Report header ──────────────────────────────────────────── */}
        <header className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 text-xs font-medium">
              {reportTypeLabel}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(report.created_at).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          </div>
          <h1 className="text-3xl font-bold text-gray-50 tracking-tight">
            {report.title}
          </h1>
          {report.description && (
            <p className="mt-2 text-gray-400 text-sm leading-relaxed">
              {report.description}
            </p>
          )}
        </header>

        {/* ── Executive summary ──────────────────────────────────────── */}
        {report.executive_summary && (
          <div className="mb-8 p-5 bg-gray-900 border border-gray-800 rounded-xl">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-2">
              Executive Summary
            </h2>
            <MarkdownContent markdown={report.executive_summary} />
          </div>
        )}

        {/* ── Methodology ────────────────────────────────────────────── */}
        {report.methodology && (
          <div className="mb-8 p-5 bg-gray-900/60 border border-gray-800 rounded-xl">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-2">
              Methodology
            </h2>
            <MarkdownContent markdown={report.methodology} />
          </div>
        )}

        {/* ── Top-level charts ───────────────────────────────────────── */}
        {report.charts && report.charts.length > 0 && (
          <div className="mb-8 grid gap-6 sm:grid-cols-1 lg:grid-cols-2">
            {report.charts.map((chart) => (
              <div
                key={chart.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5"
              >
                <ReportChart config={chart} />
              </div>
            ))}
          </div>
        )}

        {/* ── Sections ───────────────────────────────────────────────── */}
        {report.sections && report.sections.length > 0 && (
          <div className="space-y-2">
            {[...report.sections]
              .sort((a, b) => a.order - b.order)
              .map((section, idx) => (
                <SectionView key={idx} section={section} />
              ))}
          </div>
        )}

        {/* ── Fallback: full markdown content ────────────────────────── */}
        {(!report.sections || report.sections.length === 0) &&
          report.content_markdown && (
            <div className="mb-8">
              <MarkdownContent markdown={report.content_markdown} />
            </div>
          )}

        {/* ── Sources ────────────────────────────────────────────────── */}
        {report.sources && report.sources.length > 0 && (
          <SourcesList sources={report.sources} />
        )}

        {/* ── Footer ─────────────────────────────────────────────────── */}
        <SharedFooter />
      </div>
    </div>
  );
}
