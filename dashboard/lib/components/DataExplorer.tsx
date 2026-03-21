"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  exportFindingsCsvUrl,
  exportFindingsExcelUrl,
  exportFindingsJsonUrl,
} from "@/lib/api";
import { getToken } from "@/lib/auth";
import Spinner from "@/components/ui/Spinner";
import EmptyState from "@/components/ui/EmptyState";

// ── Types ────────────────────────────────────────────────────────────

interface Finding {
  id: string;
  title: string;
  category: string;
  confidence: number;
  source_type: string;
  source_url: string | null;
  content: string | null;
  structured_data: Record<string, unknown> | null;
  verified: boolean;
  created_at: string;
}

type SortDirection = "asc" | "desc";
type SortKey = keyof Pick<Finding, "title" | "category" | "confidence" | "source_type" | "verified" | "created_at">;
type GroupByKey = "none" | "category" | "source_type";

interface DataExplorerProps {
  missionId: string;
}

// ── Helpers ──────────────────────────────────────────────────────────

function confidenceVariant(c: number): string {
  if (c >= 0.8) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  if (c >= 0.5) return "bg-amber-500/10 text-amber-400 border-amber-500/20";
  return "bg-red-500/10 text-red-400 border-red-500/20";
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function compareFn(a: Finding, b: Finding, key: SortKey, dir: SortDirection): number {
  const mul = dir === "asc" ? 1 : -1;
  const valA = a[key];
  const valB = b[key];

  if (typeof valA === "number" && typeof valB === "number") {
    return (valA - valB) * mul;
  }
  if (typeof valA === "boolean" && typeof valB === "boolean") {
    return ((valA === valB ? 0 : valA ? 1 : -1)) * mul;
  }
  return String(valA ?? "").localeCompare(String(valB ?? "")) * mul;
}

// ── Sort Arrow ───────────────────────────────────────────────────────

function SortArrow({ active, dir }: { active: boolean; dir: SortDirection }) {
  if (!active) {
    return (
      <svg className="w-3.5 h-3.5 text-gray-600 ml-1 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l4-4 4 4M16 15l-4 4-4-4" />
      </svg>
    );
  }
  return dir === "asc" ? (
    <svg className="w-3.5 h-3.5 text-indigo-400 ml-1 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
    </svg>
  ) : (
    <svg className="w-3.5 h-3.5 text-indigo-400 ml-1 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}

// ── Expanded Row ─────────────────────────────────────────────────────

function ExpandedRow({ finding }: { finding: Finding }) {
  return (
    <tr>
      <td colSpan={6} className="px-4 py-4 bg-gray-800/40 border-b border-gray-800">
        <div className="space-y-3 text-sm">
          {finding.content && (
            <div>
              <p className="text-gray-500 text-xs font-medium uppercase tracking-wide mb-1">Content</p>
              <p className="text-gray-300 whitespace-pre-wrap leading-relaxed">{finding.content}</p>
            </div>
          )}
          {finding.structured_data && Object.keys(finding.structured_data).length > 0 && (
            <div>
              <p className="text-gray-500 text-xs font-medium uppercase tracking-wide mb-1">Structured Data</p>
              <pre className="text-gray-400 bg-gray-900 rounded-lg p-3 text-xs overflow-x-auto font-mono">
                {JSON.stringify(finding.structured_data, null, 2)}
              </pre>
            </div>
          )}
          {finding.source_url && (
            <div>
              <p className="text-gray-500 text-xs font-medium uppercase tracking-wide mb-1">Source URL</p>
              <a
                href={finding.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 break-all"
              >
                {finding.source_url}
              </a>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

// ── Main Component ───────────────────────────────────────────────────

export default function DataExplorer({ missionId }: DataExplorerProps) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [minConfidence, setMinConfidence] = useState(0);

  // Sort
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");

  // Group
  const [groupBy, setGroupBy] = useState<GroupByKey>("none");

  // Expanded rows
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Collapsed groups
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // ── Data fetching ──────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const url = exportFindingsJsonUrl(missionId);
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    fetch(url, { headers, cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to fetch findings (${res.status})`);
        return res.json();
      })
      .then((data: unknown) => {
        if (cancelled) return;
        const items = Array.isArray(data) ? data : [];
        setFindings(
          items.map((item: Record<string, unknown>, idx: number) => ({
            id: String(item.id ?? idx),
            title: String(item.title ?? "Untitled"),
            category: String(item.category ?? "Unknown"),
            confidence: typeof item.confidence === "number" ? item.confidence : 0,
            source_type: String(item.source_type ?? item.source ?? "unknown"),
            source_url: item.source_url ? String(item.source_url) : null,
            content: item.content ? String(item.content) : null,
            structured_data: (item.structured_data as Record<string, unknown>) ?? null,
            verified: Boolean(item.verified),
            created_at: String(item.created_at ?? new Date().toISOString()),
          })),
        );
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
  }, [missionId]);

  // ── Derived filter options ─────────────────────────────────────────

  const categories = useMemo(
    () => Array.from(new Set(findings.map((f) => f.category))).sort(),
    [findings],
  );

  const sourceTypes = useMemo(
    () => Array.from(new Set(findings.map((f) => f.source_type))).sort(),
    [findings],
  );

  // ── Filtered + sorted ──────────────────────────────────────────────

  const filteredFindings = useMemo(() => {
    const lowerSearch = search.toLowerCase();
    return findings
      .filter((f) => {
        if (lowerSearch && !f.title.toLowerCase().includes(lowerSearch) && !(f.content ?? "").toLowerCase().includes(lowerSearch)) {
          return false;
        }
        if (categoryFilter && f.category !== categoryFilter) return false;
        if (sourceFilter && f.source_type !== sourceFilter) return false;
        if (f.confidence < minConfidence) return false;
        return true;
      })
      .sort((a, b) => compareFn(a, b, sortKey, sortDir));
  }, [findings, search, categoryFilter, sourceFilter, minConfidence, sortKey, sortDir]);

  // ── Grouped ────────────────────────────────────────────────────────

  const grouped = useMemo(() => {
    if (groupBy === "none") return null;
    const map = new Map<string, Finding[]>();
    for (const f of filteredFindings) {
      const key = groupBy === "category" ? f.category : f.source_type;
      const arr = map.get(key);
      if (arr) {
        arr.push(f);
      } else {
        map.set(key, [f]);
      }
    }
    return map;
  }, [filteredFindings, groupBy]);

  // ── Handlers ───────────────────────────────────────────────────────

  const handleSort = useCallback((key: SortKey) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        return key;
      }
      setSortDir("asc");
      return key;
    });
  }, []);

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleGroup = useCallback((key: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const handleExport = useCallback(
    (format: "csv" | "json" | "excel") => {
      let url: string;
      switch (format) {
        case "csv":
          url = exportFindingsCsvUrl(missionId);
          break;
        case "json":
          url = exportFindingsJsonUrl(missionId);
          break;
        case "excel":
          url = exportFindingsExcelUrl(missionId);
          break;
      }
      window.open(url, "_blank", "noopener,noreferrer");
    },
    [missionId],
  );

  // ── Column headers ─────────────────────────────────────────────────

  const columns: Array<{ key: SortKey; label: string; className?: string }> = [
    { key: "title", label: "Title", className: "min-w-[200px]" },
    { key: "category", label: "Category" },
    { key: "confidence", label: "Confidence" },
    { key: "source_type", label: "Source" },
    { key: "verified", label: "Verified" },
    { key: "created_at", label: "Created" },
  ];

  // ── Table rows renderer ────────────────────────────────────────────

  function renderRows(items: Finding[]) {
    return items.map((f) => (
      <>
        <tr
          key={f.id}
          onClick={() => toggleExpanded(f.id)}
          className="border-b border-gray-800/60 hover:bg-gray-800/30 cursor-pointer transition-colors"
        >
          <td className="px-4 py-3 text-sm text-gray-200 font-medium max-w-[300px] truncate">
            <span className="flex items-center gap-2">
              <svg
                className={`w-3.5 h-3.5 text-gray-500 shrink-0 transition-transform ${expandedIds.has(f.id) ? "rotate-90" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              {f.title}
            </span>
          </td>
          <td className="px-4 py-3 text-sm text-gray-400">{f.category}</td>
          <td className="px-4 py-3">
            <span
              className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium ${confidenceVariant(f.confidence)}`}
            >
              {(f.confidence * 100).toFixed(0)}%
            </span>
          </td>
          <td className="px-4 py-3 text-sm text-gray-400">{f.source_type}</td>
          <td className="px-4 py-3 text-center">
            {f.verified ? (
              <svg className="w-4 h-4 text-emerald-400 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <span className="text-gray-600 text-xs">--</span>
            )}
          </td>
          <td className="px-4 py-3 text-sm text-gray-500">{formatDate(f.created_at)}</td>
        </tr>
        {expandedIds.has(f.id) && <ExpandedRow key={`${f.id}-detail`} finding={f} />}
      </>
    ));
  }

  // ── Render ─────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
        <span className="ml-3 text-gray-400 text-sm">Loading findings...</span>
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        title="Failed to load findings"
        description={error}
        icon={
          <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        }
      />
    );
  }

  if (findings.length === 0) {
    return (
      <EmptyState
        title="No findings yet"
        description="Findings will appear here once the mission discovers data."
        icon={
          <svg className="w-8 h-8 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* ── Toolbar ──────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:flex-wrap">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search findings..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
          />
        </div>

        {/* Category filter */}
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        {/* Source type filter */}
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
        >
          <option value="">All sources</option>
          {sourceTypes.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        {/* Confidence slider */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500 whitespace-nowrap">
            Min confidence: {(minConfidence * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
            className="w-24 accent-indigo-500"
          />
        </div>

        {/* Group by */}
        <select
          value={groupBy}
          onChange={(e) => {
            setGroupBy(e.target.value as GroupByKey);
            setCollapsedGroups(new Set());
          }}
          className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
        >
          <option value="none">No grouping</option>
          <option value="category">Group by Category</option>
          <option value="source_type">Group by Source Type</option>
        </select>
      </div>

      {/* ── Export buttons ───────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 mr-1">Export:</span>
        <button
          onClick={() => handleExport("csv")}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-gray-300 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          CSV
        </button>
        <button
          onClick={() => handleExport("json")}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-gray-300 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          JSON
        </button>
        <button
          onClick={() => handleExport("excel")}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-gray-300 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Excel
        </button>

        <span className="ml-auto text-xs text-gray-500">
          {filteredFindings.length} of {findings.length} findings
        </span>
      </div>

      {/* ── Table ────────────────────────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/80">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-200 select-none transition-colors ${col.className ?? ""}`}
                  >
                    {col.label}
                    <SortArrow active={sortKey === col.key} dir={sortDir} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredFindings.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-gray-500">
                    No findings match your filters.
                  </td>
                </tr>
              ) : grouped ? (
                Array.from(grouped.entries()).map(([groupKey, items]) => {
                  const isCollapsed = collapsedGroups.has(groupKey);
                  return (
                    <>
                      <tr
                        key={`group-${groupKey}`}
                        onClick={() => toggleGroup(groupKey)}
                        className="bg-gray-800/50 cursor-pointer hover:bg-gray-800/70 transition-colors"
                      >
                        <td colSpan={6} className="px-4 py-2.5">
                          <span className="flex items-center gap-2 text-sm font-medium text-gray-200">
                            <svg
                              className={`w-3.5 h-3.5 text-gray-400 transition-transform ${isCollapsed ? "" : "rotate-90"}`}
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2}
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                            </svg>
                            {groupKey}
                            <span className="inline-flex items-center rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 text-[10px] font-medium">
                              {items.length}
                            </span>
                          </span>
                        </td>
                      </tr>
                      {!isCollapsed && renderRows(items)}
                    </>
                  );
                })
              ) : (
                renderRows(filteredFindings)
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
