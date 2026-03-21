"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchProjects } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { Project } from "@/lib/types";

const TYPE_ICONS: Record<string, string> = {
  real_estate: "🏠",
  competitive_intel: "🔍",
  due_diligence: "📋",
  data_extraction: "📊",
  market_research: "📈",
  local_business: "🏪",
  custom: "⚙️",
};

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
  const { toast } = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const loadProjects = useCallback(async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch {
      setProjects([]);
      toast("Failed to load projects", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-100 tracking-tight">Projects</h1>
        <button
          onClick={() => router.push("/")}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Project
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-gray-700 border-t-emerald-400 rounded-full animate-spin" />
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-12 text-center">
          <p className="text-gray-400 mb-2">No projects yet</p>
          <button
            onClick={() => router.push("/")}
            className="text-emerald-400 hover:text-emerald-300 text-sm transition-colors"
          >
            Create your first project from the home page
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => {
            const icon = TYPE_ICONS[project.project_type] ?? TYPE_ICONS.custom;
            return (
              <button
                key={project.id}
                onClick={() => router.push(`/projects/${project.id}`)}
                className="text-left bg-gray-900 border border-gray-800/50 rounded-xl p-5 hover:border-gray-700/50 transition-colors group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="text-lg flex-shrink-0">{icon}</span>
                    <h4 className="text-gray-100 font-medium text-sm truncate group-hover:text-white transition-colors">
                      {project.name}
                    </h4>
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border whitespace-nowrap flex-shrink-0 ml-2 ${
                      TYPE_COLORS[project.project_type] ?? TYPE_COLORS.custom
                    }`}
                  >
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

                <p className="text-xs text-gray-700">{formatDate(project.created_at)}</p>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
