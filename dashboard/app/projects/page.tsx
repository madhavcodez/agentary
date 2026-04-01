"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchProjects } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { Project } from "@/lib/types";
import { TYPE_ICONS, TYPE_COLORS } from "@/lib/constants";

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
          aria-label="Create new project"
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
        <div className="glass-card rounded-xl p-12 text-center">
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
          {projects.map((project, idx) => {
            const icon = TYPE_ICONS[project.project_type] ?? TYPE_ICONS.custom;
            return (
              <button
                key={project.id}
                onClick={() => router.push(`/projects/${project.id}`)}
                onMouseEnter={() => router.prefetch(`/projects/${project.id}`)}
                className="finding-reveal text-left glass-card rounded-xl p-5 hover:border-white/[0.12] transition-all duration-[180ms] card-hover group"
                style={{ animationDelay: `${idx * 0.05}s` }}
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
