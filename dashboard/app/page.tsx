"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchProjects, createProject, fetchExpertAgents } from "@/lib/api";
import type { Project, ExpertAgent } from "@/lib/types";

const PROJECT_TYPES = [
  { value: "market_research", label: "Market Research" },
  { value: "competitive_intel", label: "Competitive Intel" },
  { value: "due_diligence", label: "Due Diligence" },
  { value: "data_extraction", label: "Data Extraction" },
  { value: "real_estate", label: "Real Estate" },
  { value: "local_business", label: "Local Business" },
  { value: "custom", label: "Custom" },
];

const TYPE_COLORS: Record<string, string> = {
  real_estate: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  competitive_intel: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  due_diligence: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  data_extraction: "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  market_research: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  local_business: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  custom: "text-gray-400 bg-gray-400/10 border-gray-400/20",
};

export default function HomePage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [agents, setAgents] = useState<ExpertAgent[]>([]);
  const [showNewProject, setShowNewProject] = useState(false);
  const [showAgents, setShowAgents] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", project_type: "market_research" });

  const loadProjects = useCallback(async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch {
      setProjects([]);
    }
  }, []);

  const loadAgents = useCallback(async () => {
    try {
      const data = await fetchExpertAgents();
      setAgents(data);
    } catch {
      setAgents([]);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSubmitting(true);
    try {
      await createProject({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        project_type: form.project_type,
      });
      setForm({ name: "", description: "", project_type: "market_research" });
      setShowNewProject(false);
      await loadProjects();
    } catch {
      // silently handle
    } finally {
      setSubmitting(false);
    }
  };

  const handleExploreAgents = () => {
    if (!showAgents) loadAgents();
    setShowAgents(!showAgents);
    setShowNewProject(false);
  };

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-gray-100 tracking-tight">
          Welcome to <span className="text-emerald-400">Agentary</span>
        </h1>
        <p className="text-gray-400 mt-2 text-lg">
          Autonomous research and intelligence platform powered by AI agents.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <button
          onClick={() => { setShowNewProject(!showNewProject); setShowAgents(false); }}
          className={`text-left bg-gray-900 border rounded-xl p-6 transition-all duration-200 hover:border-emerald-400/40 ${
            showNewProject ? "border-emerald-400/50" : "border-gray-800/50"
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-400/10 flex items-center justify-center">
              <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            </div>
            <div>
              <h3 className="text-gray-100 font-semibold">New Project</h3>
              <p className="text-gray-500 text-sm">Start a new research project</p>
            </div>
          </div>
        </button>

        <button
          onClick={handleExploreAgents}
          className={`text-left bg-gray-900 border rounded-xl p-6 transition-all duration-200 hover:border-purple-400/40 ${
            showAgents ? "border-purple-400/50" : "border-gray-800/50"
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-purple-400/10 flex items-center justify-center">
              <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
              </svg>
            </div>
            <div>
              <h3 className="text-gray-100 font-semibold">Explore Agents</h3>
              <p className="text-gray-500 text-sm">Browse expert AI agents</p>
            </div>
          </div>
        </button>
      </div>

      {showNewProject && (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-6 mb-8">
          <h3 className="text-gray-100 font-semibold mb-4">Create New Project</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Project Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Q1 Market Analysis"
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="What is this project about?"
                rows={3}
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 transition-colors resize-none"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Project Type</label>
              <select
                value={form.project_type}
                onChange={(e) => setForm({ ...form, project_type: e.target.value })}
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-emerald-400/50 transition-colors"
              >
                {PROJECT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={submitting || !form.name.trim()}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
              >
                {submitting ? "Creating..." : "Create Project"}
              </button>
              <button
                type="button"
                onClick={() => setShowNewProject(false)}
                className="px-5 py-2.5 text-gray-400 hover:text-gray-300 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {showAgents && (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-6 mb-8">
          <h3 className="text-gray-100 font-semibold mb-4">Expert Agents</h3>
          {agents.length === 0 ? (
            <p className="text-gray-500 text-sm">No agents available.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  className="bg-gray-950 border border-gray-800/50 rounded-lg p-4"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
                      style={{ backgroundColor: agent.color ? `${agent.color}20` : "rgba(52,211,153,0.1)" }}
                    >
                      {agent.icon || "🤖"}
                    </div>
                    <div>
                      <p className="text-gray-100 text-sm font-medium">{agent.name}</p>
                      <p className="text-gray-500 text-xs">{agent.specialty}</p>
                    </div>
                  </div>
                  {agent.description && (
                    <p className="text-gray-500 text-xs mt-1 line-clamp-2">{agent.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-6 mb-8">
        <h3 className="text-gray-100 font-semibold mb-5">Quick Start</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-400/10 flex items-center justify-center">
              <span className="text-emerald-400 text-sm font-bold">1</span>
            </div>
            <div>
              <p className="text-gray-100 text-sm font-medium">Create a Project</p>
              <p className="text-gray-500 text-sm mt-1">Set up a research project with context and goals.</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-400/10 flex items-center justify-center">
              <span className="text-emerald-400 text-sm font-bold">2</span>
            </div>
            <div>
              <p className="text-gray-100 text-sm font-medium">Launch Missions</p>
              <p className="text-gray-500 text-sm mt-1">Define objectives and let AI agents gather intelligence.</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-400/10 flex items-center justify-center">
              <span className="text-emerald-400 text-sm font-bold">3</span>
            </div>
            <div>
              <p className="text-gray-100 text-sm font-medium">Review Findings</p>
              <p className="text-gray-500 text-sm mt-1">Analyze results and generate comprehensive reports.</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-gray-100 font-semibold mb-4">Recent Projects</h3>
        {projects.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-12 text-center">
            <svg className="w-10 h-10 text-gray-700 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
            </svg>
            <p className="text-gray-400">No projects yet</p>
            <p className="text-sm text-gray-600 mt-1">Create your first project to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.slice(0, 6).map((project) => (
              <button
                key={project.id}
                onClick={() => router.push(`/projects/${project.id}`)}
                className="text-left bg-gray-900 border border-gray-800/50 rounded-xl p-5 hover:border-gray-700/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="text-gray-100 font-medium text-sm truncate pr-2">{project.name}</h4>
                  <span className={`text-xs px-2 py-0.5 rounded-full border whitespace-nowrap ${TYPE_COLORS[project.project_type] ?? TYPE_COLORS.custom}`}>
                    {project.project_type.replace(/_/g, " ")}
                  </span>
                </div>
                {project.description && (
                  <p className="text-gray-500 text-xs line-clamp-2 mb-3">{project.description}</p>
                )}
                <div className="flex items-center gap-4 text-xs text-gray-600">
                  <span>{project.total_missions} missions</span>
                  <span>{project.total_findings} findings</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
