"use client";

import { useEffect, useCallback } from "react";
import type { MissionFinding } from "@/lib/types";
import { sanitizeUrl } from "@/lib/security";

interface FindingModalProps {
  finding: MissionFinding;
  onClose: () => void;
  relatedFindings?: MissionFinding[];
  onSelectRelated?: (finding: MissionFinding) => void;
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const isHigh = pct >= 80;
  const color =
    isHigh
      ? "bg-emerald-500"
      : pct >= 60
        ? "bg-amber-500"
        : "bg-rose-500";
  const glowColor =
    isHigh
      ? "shadow-[0_0_12px_rgba(16,185,129,0.5)]"
      : "";
  const label =
    pct >= 80 ? "High" : pct >= 60 ? "Medium" : "Low";

  return (
    <div className="flex items-center gap-4">
      <div className="flex-1 h-2.5 bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${color} ${glowColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-medium text-gray-300 tabular-nums w-20 text-right">
        {pct}% {label}
      </span>
    </div>
  );
}

export default function FindingModal({
  finding,
  onClose,
  relatedFindings = [],
  onSelectRelated,
}: FindingModalProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [handleKeyDown]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6" role="dialog" aria-modal="true" aria-label={finding.title}>
      {/* Glass overlay */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* Modal container */}
      <div className="relative glass-modal rounded-3xl w-full max-w-2xl max-h-[85vh] overflow-hidden animate-scale-in-glass">
        {/* Header */}
        <div className="finding-reveal flex items-start justify-between gap-4 px-10 pt-10 pb-5">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2.5 mb-4">
              <span className="inline-flex items-center px-3 py-1.5 rounded-xl glass-card text-xs font-semibold text-gray-200 tracking-wide">
                {finding.category}
              </span>
              {finding.source_type && (
                <span className="inline-flex items-center px-3 py-1.5 rounded-xl glass-card text-xs text-gray-400 tracking-wide">
                  {finding.source_type}
                </span>
              )}
            </div>
            <h2 className="text-2xl font-semibold text-white/90 leading-snug tracking-tight">
              {finding.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 p-2.5 rounded-2xl text-gray-400 hover:text-white hover:bg-white/[0.1] hover:backdrop-blur-md transition-all duration-200"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Confidence */}
        <div className="finding-reveal px-10 pb-6" style={{ animationDelay: "60ms" }}>
          <ConfidenceBar value={finding.confidence} />
        </div>

        {/* Scrollable content */}
        <div className="px-10 pb-10 overflow-y-auto max-h-[55vh]">
          {/* Full content */}
          <div className="finding-reveal mb-8" style={{ animationDelay: "120ms" }}>
            <p className="text-[15px] leading-relaxed text-gray-300/90 whitespace-pre-wrap">
              {finding.content}
            </p>
          </div>

          {/* Source */}
          {(finding.source_url || finding.source_name) && (() => {
            const safeUrl = sanitizeUrl(finding.source_url);
            return (
              <div
                className="finding-reveal mb-8 p-5 glass-card rounded-2xl"
                style={{ animationDelay: "180ms" }}
              >
                <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-2.5">
                  Source
                </p>
                {safeUrl ? (
                  <a
                    href={safeUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-emerald-400 hover:text-emerald-300 transition-colors underline underline-offset-4 decoration-emerald-400/30 hover:decoration-emerald-300/60"
                  >
                    {finding.source_name || safeUrl}
                  </a>
                ) : (
                  <span className="text-sm text-gray-300">{finding.source_name || finding.source_url}</span>
                )}
              </div>
            );
          })()}

          {/* Tags */}
          {finding.tags && finding.tags.length > 0 && (
            <div className="finding-reveal mb-8" style={{ animationDelay: "240ms" }}>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-3">
                Tags
              </p>
              <div className="flex gap-2.5 flex-wrap">
                {finding.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-3.5 py-1.5 glass-card rounded-xl text-xs font-medium text-emerald-300/90 border border-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.08)]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Structured data */}
          {finding.structured_data && Object.keys(finding.structured_data).length > 0 && (
            <div className="finding-reveal mb-8" style={{ animationDelay: "300ms" }}>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-3">
                Structured Data
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {Object.entries(finding.structured_data).map(([key, value]) => (
                  <div
                    key={key}
                    className="glass-card rounded-2xl p-4"
                  >
                    <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
                      {key}
                    </p>
                    <p className="text-sm text-gray-200 break-words leading-relaxed">
                      {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Related findings */}
          {relatedFindings.length > 0 && (
            <div className="finding-reveal" style={{ animationDelay: "360ms" }}>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-4">
                Related Findings
              </p>
              <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/10">
                {relatedFindings.slice(0, 6).map((rf) => (
                  <button
                    key={rf.id}
                    onClick={() => onSelectRelated?.(rf)}
                    className="flex-shrink-0 w-56 text-left p-4 glass-card rounded-2xl hover:border-white/[0.15] hover:shadow-[0_0_20px_rgba(255,255,255,0.04)] transition-all duration-200 group"
                  >
                    <span className="text-sm text-gray-200 font-medium line-clamp-2 group-hover:text-white transition-colors">
                      {rf.title}
                    </span>
                    <div className="flex items-center gap-2 mt-3">
                      <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            rf.confidence >= 0.8
                              ? "bg-emerald-500/70"
                              : rf.confidence >= 0.6
                                ? "bg-amber-500/70"
                                : "bg-rose-500/70"
                          }`}
                          style={{ width: `${Math.round(rf.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-gray-500 tabular-nums font-medium">
                        {Math.round(rf.confidence * 100)}%
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
