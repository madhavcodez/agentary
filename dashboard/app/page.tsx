"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchProjects, createProject } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
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
  const { toast } = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [projectName, setProjectName] = useState("");
  const [creating, setCreating] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const loadProjects = useCallback(async () => {
    try {
      setLoadError(false);
      const data = await fetchProjects();
      setProjects(data);
    } catch {
      setLoadError(true);
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
      toast("Failed to create project", "error");
      setCreating(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-8 py-10">
      {/* Hero */}
      <div className="mb-10">
        <h1 className="text-2xl font-editorial font-bold text-gray-100 tracking-tight">
          New Research
        </h1>
        <p className="text-gray-500 mt-1.5 text-sm">
          Pick a template and launch your agents.
        </p>
      </div>

      {/* Type Selection */}
      <div className="mb-8" role="radiogroup" aria-label="Research type">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.type}
              role="radio"
              aria-checked={selectedType === t.type}
              onClick={() => handleSelectType(t.type)}
              className={`text-left px-4 py-3.5 rounded-xl border transition-all duration-[180ms] ${
                selectedType === t.type
                  ? "bg-emerald-500/10 border-emerald-500/20 ring-1 ring-emerald-500/10"
                  : "glass-card card-hover hover:border-white/[0.12]"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="text-lg">{t.icon}</span>
                <span className={`text-sm font-medium ${selectedType === t.type ? "text-emerald-400" : "text-gray-200"}`}>
                  {t.label}
                </span>
              </div>
              <div className="text-[11px] text-gray-500 mt-1.5 leading-relaxed pl-[30px]">{t.hint}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Name + Create -- appears after type selection */}
      {selectedType && (
        <div className="mb-10 animate-slide-up">
          <div className="flex gap-3">
            <label htmlFor="project-name" className="sr-only">Project name</label>
            <input
              id="project-name"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !creating && handleCreate()}
              placeholder="Name your project..."
              autoFocus
              className="flex-1 glass-card rounded-xl px-5 py-3 text-sm text-gray-100 placeholder-gray-600 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20 transition-all duration-[180ms]"
            />
            <button
              onClick={handleCreate}
              disabled={creating || !projectName.trim()}
              className="px-7 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-[#1a2030] disabled:text-gray-600 text-white text-sm font-semibold rounded-xl transition-all duration-[180ms] whitespace-nowrap"
            >
              {creating ? "Creating..." : "Create Project"}
            </button>
          </div>
        </div>
      )}

      {/* Load Error */}
      {loadError && projects.length === 0 && (
        <div className="mb-6 glass-card rounded-xl p-4 flex items-center justify-between border-red-500/15">
          <p className="text-sm text-red-400">Failed to load recent projects.</p>
          <button onClick={loadProjects} className="text-xs text-red-400 hover:text-red-300 underline transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* Recent Projects */}
      {projects.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-3">
            Recent projects
          </p>
          <div className="space-y-1.5">
            {projects.slice(0, 5).map((p) => (
              <button
                key={p.id}
                onClick={() => router.push(`/projects/${p.id}`)}
                onMouseEnter={() => router.prefetch(`/projects/${p.id}`)}
                className="w-full text-left flex items-center gap-3.5 px-4 py-3 glass-card rounded-xl hover:border-white/[0.12] transition-all duration-[180ms] card-hover"
              >
                <div className="text-base">
                  {TEMPLATES.find((t) => t.type === p.project_type)?.icon ?? "\u{1F4C1}"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-200 font-medium truncate">{p.name}</div>
                  <div className="text-[11px] text-gray-500 mt-0.5">
                    {p.total_missions} missions · {p.total_findings} findings
                  </div>
                </div>
                <div className="text-[11px] text-gray-600">
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
