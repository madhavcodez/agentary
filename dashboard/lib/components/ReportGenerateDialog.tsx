"use client";

import { useState, useCallback } from "react";
import { createReport } from "@/lib/api";
import type { ReportType } from "@/lib/types";
import Dialog from "@/components/ui/Dialog";
import Button from "@/components/ui/Button";

// ── Types ────────────────────────────────────────────────────────────

interface ReportGenerateDialogProps {
  missionId: string;
  missionTitle: string;
  findingsCount: number;
  sourcesCount: number;
  onClose: () => void;
  onGenerated: (reportId: string) => void;
}

interface ReportTypeOption {
  value: ReportType;
  label: string;
  description: string;
}

const REPORT_TYPES: readonly ReportTypeOption[] = [
  {
    value: "research_report",
    label: "Research Report",
    description: "Comprehensive research summary with analysis",
  },
  {
    value: "market_analysis",
    label: "Market Analysis",
    description: "Market trends, sizing, and competitive landscape",
  },
  {
    value: "property_report",
    label: "Property Report",
    description: "Real estate and property assessment details",
  },
  {
    value: "competitive_intel",
    label: "Competitive Intel",
    description: "Competitor analysis and positioning insights",
  },
  {
    value: "due_diligence",
    label: "Due Diligence",
    description: "Thorough investigation and verification report",
  },
] as const;

interface ContentOption {
  key: string;
  label: string;
  configKey: string;
}

const CONTENT_OPTIONS: readonly ContentOption[] = [
  { key: "charts", label: "Include charts", configKey: "include_charts" },
  { key: "tables", label: "Data tables", configKey: "include_tables" },
  { key: "sources", label: "Sources", configKey: "include_sources" },
] as const;

// ── Component ────────────────────────────────────────────────────────

export default function ReportGenerateDialog({
  missionId,
  missionTitle,
  findingsCount,
  sourcesCount,
  onClose,
  onGenerated,
}: ReportGenerateDialogProps) {
  const [reportType, setReportType] = useState<ReportType>("research_report");
  const [contentFlags, setContentFlags] = useState<Record<string, boolean>>({
    charts: true,
    tables: true,
    sources: true,
  });
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleFlag = useCallback((key: string) => {
    setContentFlags((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  }, []);

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setError(null);

    try {
      const config: Record<string, unknown> = {};
      for (const opt of CONTENT_OPTIONS) {
        config[opt.configKey] = contentFlags[opt.key] ?? false;
      }

      const report = await createReport({
        mission_id: missionId,
        report_type: reportType,
        config,
      });

      onGenerated(report.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to generate report";
      setError(message);
    } finally {
      setGenerating(false);
    }
  }, [missionId, reportType, contentFlags, onGenerated]);

  return (
    <Dialog open onClose={onClose} className="max-w-md">
      <div className="px-6 py-5">
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-500/10 mb-3">
            <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-100">Mission Complete!</h3>
          <p className="text-sm text-gray-400 mt-1">
            {missionTitle}
          </p>
          <div className="flex items-center justify-center gap-4 mt-3">
            <span className="inline-flex items-center gap-1.5 text-sm text-gray-300">
              <svg className="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              {findingsCount} findings
            </span>
            <span className="inline-flex items-center gap-1.5 text-sm text-gray-300">
              <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
              </svg>
              {sourcesCount} sources
            </span>
          </div>
        </div>

        {/* ── Report type selector ───────────────────────────────────── */}
        <div className="mb-5">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2.5">
            Report Type
          </p>
          <div className="space-y-2">
            {REPORT_TYPES.map((opt) => (
              <label
                key={opt.value}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  reportType === opt.value
                    ? "border-indigo-500/50 bg-indigo-500/5"
                    : "border-gray-800 bg-gray-900 hover:border-gray-700"
                }`}
              >
                <input
                  type="radio"
                  name="reportType"
                  value={opt.value}
                  checked={reportType === opt.value}
                  onChange={() => setReportType(opt.value)}
                  className="mt-0.5 accent-indigo-500"
                />
                <div>
                  <span className="text-sm font-medium text-gray-200">{opt.label}</span>
                  <p className="text-xs text-gray-500 mt-0.5">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* ── Content options ────────────────────────────────────────── */}
        <div className="mb-6">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2.5">
            Content Options
          </p>
          <div className="space-y-2">
            {CONTENT_OPTIONS.map((opt) => (
              <label
                key={opt.key}
                className="flex items-center gap-3 p-2.5 rounded-lg border border-gray-800 bg-gray-900 cursor-pointer hover:border-gray-700 transition-colors"
              >
                <input
                  type="checkbox"
                  checked={contentFlags[opt.key] ?? false}
                  onChange={() => toggleFlag(opt.key)}
                  className="accent-indigo-500 rounded"
                />
                <span className="text-sm text-gray-300">{opt.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* ── Error message ──────────────────────────────────────────── */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* ── Actions ────────────────────────────────────────────────── */}
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="md"
            onClick={onClose}
            disabled={generating}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={handleGenerate}
            loading={generating}
            className="flex-1"
            icon={
              !generating ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              ) : undefined
            }
          >
            {generating ? "Generating..." : "Generate Report"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
