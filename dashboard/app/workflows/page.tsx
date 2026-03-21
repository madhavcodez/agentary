"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchWorkflows, triggerWorkflowRun, deleteWorkflow } from "@/lib/api";
import type { WorkflowData } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-700/50 text-gray-300",
  active: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  paused: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  archived: "bg-gray-600/30 text-gray-500",
};

const TRIGGER_LABELS: Record<string, string> = {
  manual: "Manual",
  scheduled: "Scheduled",
  event: "Event-driven",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningIds, setRunningIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadWorkflows();
  }, []);

  async function loadWorkflows() {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchWorkflows({});
      // fetchWorkflows returns Workflow[] (slim), but we cast to WorkflowData[]
      // since the API may return full objects; handle missing fields gracefully
      setWorkflows(data as unknown as WorkflowData[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }

  async function handleRun(id: string) {
    try {
      setRunningIds((prev) => new Set([...prev, id]));
      await triggerWorkflowRun(id);
      await loadWorkflows();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger workflow run");
    } finally {
      setRunningIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete workflow "${name}"? This cannot be undone.`)) return;
    try {
      await deleteWorkflow(id);
      setWorkflows((prev) => prev.filter((w) => w.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete workflow");
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold text-gray-100">Workflows</h1>
        <Link
          href="/workflows/new"
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          New Workflow
        </Link>
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
      ) : workflows.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-16 text-center">
          <div className="text-gray-500 mb-2 text-4xl">&#9881;</div>
          <p className="text-gray-400 font-medium">No workflows yet.</p>
          <p className="text-gray-500 text-sm mt-1">
            Create your first automation.
          </p>
          <Link
            href="/workflows/new"
            className="inline-block mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            New Workflow
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {workflows.map((wf) => {
            const status = (wf as unknown as WorkflowData).status ?? "draft";
            const triggerType = (wf as unknown as WorkflowData).trigger_type ?? "manual";
            const nodes = (wf as unknown as WorkflowData).nodes ?? [];
            const lastRunAt = (wf as unknown as WorkflowData).last_run_at ?? null;
            const totalRuns = (wf as unknown as WorkflowData).total_runs ?? 0;

            return (
              <div
                key={wf.id}
                className="bg-gray-900 border border-gray-800/50 rounded-xl p-5 flex flex-col justify-between hover:border-gray-700/60 transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-gray-100 font-medium truncate pr-2">
                      {wf.name}
                    </h3>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${STATUS_STYLES[status] ?? STATUS_STYLES.draft}`}
                    >
                      {status}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 mb-4">
                    <span>{TRIGGER_LABELS[triggerType] ?? triggerType}</span>
                    <span>{nodes.length} node{nodes.length !== 1 ? "s" : ""}</span>
                    <span>{totalRuns} run{totalRuns !== 1 ? "s" : ""}</span>
                  </div>

                  <p className="text-xs text-gray-500">
                    Last run: {formatDate(lastRunAt)}
                  </p>
                </div>

                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-800/50">
                  <Link
                    href={`/workflows/${wf.id}`}
                    className="px-3 py-1.5 text-xs font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-md transition-colors"
                  >
                    Edit
                  </Link>
                  <button
                    onClick={() => handleRun(wf.id)}
                    disabled={runningIds.has(wf.id)}
                    className="px-3 py-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-md transition-colors disabled:opacity-50"
                  >
                    {runningIds.has(wf.id) ? "Running..." : "Run"}
                  </button>
                  <button
                    onClick={() => handleDelete(wf.id, wf.name)}
                    className="px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/10 rounded-md transition-colors ml-auto"
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
