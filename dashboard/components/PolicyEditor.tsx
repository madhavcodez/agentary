"use client";

import { useState } from "react";

interface PolicyEditorProps {
  initialName?: string;
  initialDescription?: string;
  initialRulesJson?: string;
  initialActive?: boolean;
  onSave: (data: {
    name: string;
    description: string;
    rules_json: Record<string, unknown> | unknown[];
    is_active: boolean;
  }) => Promise<void>;
  onCancel: () => void;
  saving?: boolean;
}

export default function PolicyEditor({
  initialName = "",
  initialDescription = "",
  initialRulesJson = '{\n  "conditions": [],\n  "actions": []\n}',
  initialActive = true,
  onSave,
  onCancel,
  saving = false,
}: PolicyEditorProps) {
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [rulesJson, setRulesJson] = useState(initialRulesJson);
  const [isActive, setIsActive] = useState(initialActive);
  const [jsonError, setJsonError] = useState<string | null>(null);

  function validateJson(value: string): boolean {
    try {
      JSON.parse(value);
      setJsonError(null);
      return true;
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : "Invalid JSON");
      return false;
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!name.trim()) return;
    if (!validateJson(rulesJson)) return;

    await onSave({
      name: name.trim(),
      description: description.trim(),
      rules_json: JSON.parse(rulesJson),
      is_active: isActive,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Name */}
      <div>
        <label htmlFor="policy-name" className="block text-sm font-medium text-gray-300 mb-1.5">
          Policy Name
        </label>
        <input
          id="policy-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Remote-only filter"
          required
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
        />
      </div>

      {/* Description */}
      <div>
        <label htmlFor="policy-desc" className="block text-sm font-medium text-gray-300 mb-1.5">
          Description
        </label>
        <input
          id="policy-desc"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What does this policy do?"
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors"
        />
      </div>

      {/* Rules JSON */}
      <div>
        <label htmlFor="policy-rules" className="block text-sm font-medium text-gray-300 mb-1.5">
          Rules (JSON)
        </label>
        <textarea
          id="policy-rules"
          value={rulesJson}
          onChange={(e) => {
            setRulesJson(e.target.value);
            if (jsonError) validateJson(e.target.value);
          }}
          onBlur={() => validateJson(rulesJson)}
          rows={10}
          className={`w-full bg-gray-800 border rounded-lg px-4 py-3 text-sm text-gray-100 font-mono placeholder-gray-500 focus:outline-none focus:ring-2 transition-colors resize-y ${
            jsonError
              ? "border-red-500/50 focus:ring-red-500/50 focus:border-red-500"
              : "border-gray-700 focus:ring-indigo-500/50 focus:border-indigo-500"
          }`}
        />
        {jsonError && (
          <p className="mt-1.5 text-xs text-red-400">JSON Error: {jsonError}</p>
        )}
      </div>

      {/* Active toggle */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setIsActive(!isActive)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            isActive ? "bg-indigo-500" : "bg-gray-700"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
              isActive ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
        <span className="text-sm text-gray-300">
          {isActive ? "Active" : "Inactive"}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
        >
          {saving ? "Saving..." : "Save Policy"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg border border-gray-700 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
