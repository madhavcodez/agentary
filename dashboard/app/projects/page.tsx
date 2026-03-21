"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchProjects, createProject } from "@/lib/api";
import type { Project } from "@/lib/types";

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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", project_type: "market_research" });

  const loadProjects = useCallback(async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
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
      setShowForm(false);
      await loadProjects();
    } catch {
      // silently handle
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-100 tracking-tight">Projects</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          New Project
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-6 mb-6">
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
                onClick={() => setShowForm(false)}
                className="px-5 py-2.5 text-gray-400 hover:text-gray-300 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-gray-700 border-t-emerald-400 rounded-full animate-spin" />
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-12 text-center">
          <svg className="w-10 h-10 text-gray-700 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
          </svg>
          <p className="text-gray-400">No projects yet</p>
          <p className="text-sm text-gray-600 mt-1">Create your first research project to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
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
              <div className="flex items-center gap-4 text-xs text-gray-600 mb-2">
                <span>{project.total_missions} missions</span>
                <span>{project.total_findings} findings</span>
                <span>{project.total_reports_generated} reports</span>
              </div>
              <p className="text-xs text-gray-600">{formatDate(project.created_at)}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
