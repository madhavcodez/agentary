"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchProjects, createProject } from "@/lib/api";
import type { Project } from "@/lib/types";

const TEMPLATES = [
  {
    type: "real_estate",
    icon: "🏠",
    label: "Real Estate",
    hint: "Analyze properties, prices, and market trends",
    nameSuggestion: "Real Estate Market Analysis",
  },
  {
    type: "competitive_intel",
    icon: "🔍",
    label: "Competitive Intel",
    hint: "Track competitors, pricing, and market moves",
    nameSuggestion: "Competitive Intelligence Report",
  },
  {
    type: "market_research",
    icon: "📊",
    label: "Market Research",
    hint: "Understand markets, demand signals, and gaps",
    nameSuggestion: "Market Research Study",
  },
  {
    type: "due_diligence",
    icon: "📋",
    label: "Due Diligence",
    hint: "Deep research before deals and investments",
    nameSuggestion: "Due Diligence Investigation",
  },
  {
    type: "local_business",
    icon: "🏪",
    label: "Local Business",
    hint: "Survey local businesses, prices, and services",
    nameSuggestion: "Local Business Survey",
  },
  {
    type: "custom",
    icon: "⚡",
    label: "Custom Research",
    hint: "Define your own research objective",
    nameSuggestion: "Research Project",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [projectName, setProjectName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadProjects = useCallback(async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  function handleSelectType(type: string) {
    setSelectedType(type);
    const template = TEMPLATES.find((t) => t.type === type);
    if (template) setProjectName(template.nameSuggestion);
  }

  async function handleCreate() {
    if (!selectedType || !projectName.trim()) return;
    setCreating(true);
    try {
      const project = await createProject({
        name: projectName.trim(),
        project_type: selectedType,
      });
      router.push(`/projects/${project.id}`);
    } catch {
      setCreating(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-8 py-16">
      {/* Hero */}
      <div className="mb-12">
        <h1 className="text-3xl font-bold text-gray-100 tracking-tight">
          Welcome to Agentary
        </h1>
        <p className="text-gray-500 mt-2 text-lg">
          Deploy AI agents that research, analyze, and report — automatically.
        </p>
      </div>

      {/* Type Selection */}
      <div className="mb-8">
        <p className="text-sm font-medium text-gray-400 mb-4">
          What would you like to research?
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.type}
              onClick={() => handleSelectType(t.type)}
              className={`text-left p-4 rounded-xl border transition-all duration-150 ${
                selectedType === t.type
                  ? "bg-emerald-500/10 border-emerald-500/30 ring-1 ring-emerald-500/20"
                  : "bg-gray-900 border-gray-800/50 hover:border-gray-700/60 hover:bg-gray-900/80"
              }`}
            >
              <div className="text-2xl mb-2">{t.icon}</div>
              <div className={`text-sm font-medium ${selectedType === t.type ? "text-emerald-400" : "text-gray-200"}`}>
                {t.label}
              </div>
              <div className="text-xs text-gray-500 mt-1">{t.hint}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Name + Create — appears after type selection */}
      {selectedType && (
        <div className="mb-16 animate-in fade-in duration-200">
          <div className="flex gap-3">
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              placeholder="Name your project..."
              autoFocus
              className="flex-1 bg-gray-900 border border-gray-800/50 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20 transition-all"
            />
            <button
              onClick={handleCreate}
              disabled={creating || !projectName.trim()}
              className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-800 disabled:text-gray-600 text-white text-sm font-medium rounded-xl transition-colors whitespace-nowrap"
            >
              {creating ? "Creating..." : "Create Project →"}
            </button>
          </div>
        </div>
      )}

      {/* Quick Start */}
      {!selectedType && (
        <div className="mb-16 bg-gray-900/50 border border-gray-800/30 rounded-xl p-6">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-4">
            How it works
          </p>
          <div className="grid grid-cols-3 gap-6">
            {[
              { step: "1", title: "Pick a type", desc: "Choose what you want to research" },
              { step: "2", title: "Define a mission", desc: "Tell agents what to find" },
              { step: "3", title: "Get results", desc: "Findings, reports, data — automatically" },
            ].map((s) => (
              <div key={s.step} className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-gray-800 text-gray-500 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                  {s.step}
                </div>
                <div>
                  <div className="text-sm text-gray-300 font-medium">{s.title}</div>
                  <div className="text-xs text-gray-600 mt-0.5">{s.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Projects */}
      {projects.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Recent projects
          </p>
          <div className="space-y-2">
            {projects.slice(0, 5).map((p) => (
              <button
                key={p.id}
                onClick={() => router.push(`/projects/${p.id}`)}
                className="w-full text-left flex items-center gap-4 px-4 py-3 bg-gray-900 border border-gray-800/50 rounded-xl hover:border-gray-700/60 transition-colors"
              >
                <div className="text-lg">
                  {TEMPLATES.find((t) => t.type === p.project_type)?.icon ?? "📁"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-200 font-medium truncate">{p.name}</div>
                  <div className="text-xs text-gray-600 mt-0.5">
                    {p.total_missions} missions · {p.total_findings} findings
                  </div>
                </div>
                <div className="text-xs text-gray-600">
                  {new Date(p.created_at).toLocaleDateString()}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
