"use client";

import Link from "next/link";
import type { WorkflowData } from "@/lib/types";

interface Props {
  workflow: WorkflowData;
  dirty: boolean;
  saving: boolean;
  validationErrors: string[];
  onSave: () => void;
  onValidate: () => Promise<boolean>;
  onRun: () => void;
  onActivate: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-600",
  active: "bg-emerald-600",
  paused: "bg-amber-600",
  archived: "bg-gray-700",
};

export default function WorkflowToolbar({
  workflow,
  dirty,
  saving,
  validationErrors,
  onSave,
  onValidate,
  onRun,
  onActivate,
}: Props) {
  return (
    <div className="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <Link
          href="/workflows"
          className="text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          &larr; Workflows
        </Link>
        <span className="text-gray-700">/</span>
        <h2 className="text-sm font-semibold text-gray-200 truncate max-w-[200px]">
          {workflow.name}
        </h2>
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-medium text-white ${
            STATUS_COLORS[workflow.status] || "bg-gray-600"
          }`}
        >
          {workflow.status}
        </span>
        {dirty && (
          <span className="text-[10px] text-amber-400 font-medium">Unsaved changes</span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {validationErrors.length > 0 && (
          <span className="text-xs text-red-400 mr-2">
            {validationErrors.length} error{validationErrors.length !== 1 && "s"}
          </span>
        )}
        <button
          onClick={onSave}
          disabled={saving || !dirty}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-gray-200 rounded text-xs font-medium transition-colors border border-gray-700"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          onClick={onValidate}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded text-xs font-medium transition-colors border border-gray-700"
        >
          Validate
        </button>
        <button
          onClick={onRun}
          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition-colors"
        >
          Run
        </button>
        <button
          onClick={onActivate}
          className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            workflow.status === "active"
              ? "bg-amber-600 hover:bg-amber-500 text-white"
              : "bg-emerald-600 hover:bg-emerald-500 text-white"
          }`}
        >
          {workflow.status === "active" ? "Pause" : "Activate"}
        </button>
        <Link
          href={`/workflows/${workflow.id}/runs/${workflow.id}`}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded text-xs font-medium transition-colors border border-gray-700"
        >
          Runs
        </Link>
      </div>
    </div>
  );
}
