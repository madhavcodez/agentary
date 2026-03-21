"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { fetchWorkflows, deleteWorkflow } from "@/lib/api";
import type { WorkflowData } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-600",
  active: "bg-emerald-600",
  paused: "bg-amber-600",
  archived: "bg-gray-700",
};

export default function WorkflowsPage() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<WorkflowData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWorkflows({ limit: 50 })
      .then((res) => setWorkflows(res.items))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: string) {
    if (!confirm("Delete this workflow?")) return;
    await deleteWorkflow(id);
    setWorkflows((prev) => prev.filter((w) => w.id !== id));
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Nav />
      <main className="ml-64 p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">Workflows</h1>
            <p className="text-sm text-gray-400 mt-1">
              Automate research pipelines with visual workflows
            </p>
          </div>
          <Link
            href="/workflows/new"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            + New Workflow
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : workflows.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-4xl mb-4">&#9881;</div>
            <h2 className="text-lg font-medium text-gray-300">No workflows yet</h2>
            <p className="text-sm text-gray-500 mt-2">
              Create your first workflow from a template, natural language, or the visual editor.
            </p>
            <Link
              href="/workflows/new"
              className="inline-block mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm"
            >
              Create Workflow
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workflows.map((wf) => (
              <div
                key={wf.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors cursor-pointer group"
                onClick={() => router.push(`/workflows/${wf.id}`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-gray-100 group-hover:text-indigo-400 transition-colors truncate">
                    {wf.name}
                  </h3>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium text-white ${STATUS_COLORS[wf.status] || "bg-gray-600"}`}
                  >
                    {wf.status}
                  </span>
                </div>
                {wf.description && (
                  <p className="text-sm text-gray-400 mb-3 line-clamp-2">{wf.description}</p>
                )}
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>{wf.nodes.length} nodes</span>
                  <span>{wf.total_runs} runs</span>
                  <span>{wf.trigger_type}</span>
                </div>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-800">
                  <span className="text-xs text-gray-500">
                    {new Date(wf.updated_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(wf.id);
                    }}
                    className="text-xs text-gray-600 hover:text-red-400 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
