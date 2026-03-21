"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import {
  createWorkflow,
  createWorkflowFromDescription,
  createWorkflowFromTemplate,
  fetchWorkflowTemplates,
} from "@/lib/api";
import type { WorkflowTemplate, WorkflowVariableSchema } from "@/lib/types";

export default function NewWorkflowPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"choose" | "template" | "nl" | "blank">("choose");
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [nlDescription, setNlDescription] = useState("");
  const [blankName, setBlankName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchWorkflowTemplates()
      .then(setTemplates)
      .catch(() => setError("Failed to load templates"));
  }, []);

  async function handleTemplateCreate() {
    if (!selectedTemplate) return;
    setLoading(true);
    setError("");
    try {
      const wf = await createWorkflowFromTemplate({
        template_id: selectedTemplate.id,
        variables,
        name: `${selectedTemplate.name}`,
      });
      router.push(`/workflows/${wf.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create workflow");
    } finally {
      setLoading(false);
    }
  }

  async function handleNLCreate() {
    if (!nlDescription.trim()) return;
    setLoading(true);
    setError("");
    try {
      const wf = await createWorkflowFromDescription({ description: nlDescription });
      router.push(`/workflows/${wf.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate workflow");
    } finally {
      setLoading(false);
    }
  }

  async function handleBlankCreate() {
    if (!blankName.trim()) return;
    setLoading(true);
    setError("");
    try {
      const wf = await createWorkflow({
        name: blankName,
        nodes: [{ id: "trigger_1", type: "manual_trigger", label: "Start", config: {}, position: { x: 250, y: 50 } }],
        edges: [],
        created_from: "visual_editor",
      });
      router.push(`/workflows/${wf.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create workflow");
    } finally {
      setLoading(false);
    }
  }

  const CATEGORY_LABELS: Record<string, string> = {
    real_estate: "Real Estate",
    competitive_intel: "Competitive Intel",
    local_business: "Local Business",
    due_diligence: "Due Diligence",
    price_monitoring: "Price Monitoring",
    people_research: "People Research",
    custom: "Custom",
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Nav />
      <main className="ml-64 p-8 max-w-4xl">
        <h1 className="text-2xl font-bold mb-2">Create Workflow</h1>
        <p className="text-sm text-gray-400 mb-8">Choose how to create your workflow</p>

        {error && (
          <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-300">
            {error}
          </div>
        )}

        {mode === "choose" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => setMode("template")}
              className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-left hover:border-indigo-500/50 transition-colors"
            >
              <div className="text-2xl mb-3">&#128196;</div>
              <h3 className="font-semibold mb-1">From Template</h3>
              <p className="text-sm text-gray-400">
                Start with a pre-built workflow and customize the parameters.
              </p>
            </button>
            <button
              onClick={() => setMode("nl")}
              className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-left hover:border-indigo-500/50 transition-colors"
            >
              <div className="text-2xl mb-3">&#128172;</div>
              <h3 className="font-semibold mb-1">Natural Language</h3>
              <p className="text-sm text-gray-400">
                Describe what you want in plain English. AI builds the workflow.
              </p>
            </button>
            <button
              onClick={() => setMode("blank")}
              className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-left hover:border-indigo-500/50 transition-colors"
            >
              <div className="text-2xl mb-3">&#9998;</div>
              <h3 className="font-semibold mb-1">Blank Canvas</h3>
              <p className="text-sm text-gray-400">
                Start from scratch with the visual node editor.
              </p>
            </button>
          </div>
        )}

        {mode === "template" && (
          <div>
            <button onClick={() => { setMode("choose"); setSelectedTemplate(null); }} className="text-sm text-gray-400 hover:text-gray-200 mb-4">
              &larr; Back
            </button>
            {!selectedTemplate ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {templates.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => {
                      setSelectedTemplate(t);
                      const defaults: Record<string, string> = {};
                      t.variables_schema.forEach((v) => {
                        defaults[v.name] = String(v.default ?? "");
                      });
                      setVariables(defaults);
                    }}
                    className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-left hover:border-indigo-500/50 transition-colors"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-0.5 bg-indigo-900/40 text-indigo-300 rounded text-xs">
                        {CATEGORY_LABELS[t.category] || t.category}
                      </span>
                      {t.is_system && (
                        <span className="px-2 py-0.5 bg-gray-800 text-gray-400 rounded text-xs">System</span>
                      )}
                    </div>
                    <h3 className="font-semibold mb-1">{t.name}</h3>
                    <p className="text-sm text-gray-400 line-clamp-2">{t.description}</p>
                    <div className="text-xs text-gray-500 mt-2">
                      {t.nodes_template.length} nodes &middot; {t.install_count} installs
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h3 className="font-semibold text-lg mb-1">{selectedTemplate.name}</h3>
                <p className="text-sm text-gray-400 mb-4">{selectedTemplate.description}</p>
                <div className="space-y-3 mb-6">
                  {selectedTemplate.variables_schema.map((v: WorkflowVariableSchema) => (
                    <div key={v.name}>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        {v.label || v.name} {v.required && <span className="text-red-400">*</span>}
                      </label>
                      {v.description && <p className="text-xs text-gray-500 mb-1">{v.description}</p>}
                      <input
                        type="text"
                        value={variables[v.name] || ""}
                        onChange={(e) => setVariables({ ...variables, [v.name]: e.target.value })}
                        placeholder={String(v.default || "")}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
                <button
                  onClick={handleTemplateCreate}
                  disabled={loading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
                >
                  {loading ? "Creating..." : "Create Workflow"}
                </button>
              </div>
            )}
          </div>
        )}

        {mode === "nl" && (
          <div>
            <button onClick={() => setMode("choose")} className="text-sm text-gray-400 hover:text-gray-200 mb-4">
              &larr; Back
            </button>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="font-semibold text-lg mb-3">Describe Your Workflow</h3>
              <textarea
                value={nlDescription}
                onChange={(e) => setNlDescription(e.target.value)}
                placeholder="Every Monday, check gas prices at stations within 5 miles, call any without online prices, compile comparison, email me the results..."
                rows={4}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none resize-none"
              />
              <button
                onClick={handleNLCreate}
                disabled={loading || !nlDescription.trim()}
                className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
              >
                {loading ? "Generating..." : "Generate Workflow"}
              </button>
            </div>
          </div>
        )}

        {mode === "blank" && (
          <div>
            <button onClick={() => setMode("choose")} className="text-sm text-gray-400 hover:text-gray-200 mb-4">
              &larr; Back
            </button>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="font-semibold text-lg mb-3">Blank Workflow</h3>
              <input
                type="text"
                value={blankName}
                onChange={(e) => setBlankName(e.target.value)}
                placeholder="My Workflow"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none mb-4"
              />
              <button
                onClick={handleBlankCreate}
                disabled={loading || !blankName.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
              >
                {loading ? "Creating..." : "Create & Open Editor"}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
