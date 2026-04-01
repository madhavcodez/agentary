"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  fetchProject,
  fetchMissions,
  fetchReports,
  createMission,
} from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { Project, Mission } from "@/lib/types";
import { TYPE_ICONS } from "@/lib/constants";
import { ProjectSkeleton } from "@/components/ui/Skeleton";
import ProjectOnboarding from "@/components/project/ProjectOnboarding";
import StatBadge from "@/components/ui/StatBadge";
import StatusDot from "@/components/ui/StatusDot";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

/* ────────────────────────────────────────────────────────────────────
 * Main Page
 * ──────────────────────────────────────────────────────────────────── */

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const id = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [reportsCount, setReportsCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [missionInput, setMissionInput] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadProject = useCallback(async () => {
    try {
      const data = await fetchProject(id);
      setProject(data);
    } catch {
      setProject(null);
      toast("Failed to load project", "error");
    } finally {
      setLoading(false);
    }
  }, [id, toast]);

  const loadMissions = useCallback(async () => {
    try {
      const data = await fetchMissions({ project_id: id });
      setMissions(data);
    } catch {
      setMissions([]);
      toast("Failed to load missions", "error");
    }
  }, [id, toast]);

  const loadReports = useCallback(async () => {
    try {
      const data = await fetchReports({ project_id: id });
      setReportsCount(data.length);
    } catch {
      setReportsCount(0);
    }
  }, [id]);

  useEffect(() => {
    loadProject();
    loadMissions();
    loadReports();
  }, [loadProject, loadMissions, loadReports]);

  const handleCreateMission = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = missionInput.trim();
    if (!name) return;
    setSubmitting(true);
    try {
      const mission = await createMission({
        project_id: id,
        name,
        mission_type: "research",
      });
      router.push(`/missions/${mission.id}`);
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Failed to create mission", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <ProjectSkeleton />;
  }

  if (!project) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <div className="glass-card rounded-2xl border border-gray-800/40 p-12 text-center">
          <p className="text-gray-400">Project not found.</p>
          <button
            onClick={() => router.push("/projects")}
            className="text-emerald-400 hover:text-emerald-300 text-sm mt-3 transition-colors"
          >
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  const icon = TYPE_ICONS[project.project_type] ?? TYPE_ICONS.custom;
  const isNewProject = missions.length === 0;

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      {/* Back link */}
      <button
        onClick={() => router.push("/projects")}
        className="text-gray-500 hover:text-gray-300 text-sm mb-6 transition-colors flex items-center gap-1.5"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Projects
      </button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">{icon}</span>
        <h1 className="text-2xl font-bold text-gray-100 tracking-tight">
          {project.name}
        </h1>
        <span className="text-xs px-2.5 py-0.5 rounded-full border border-gray-700 text-gray-400 capitalize">
          {project.project_type.replace(/_/g, " ")}
        </span>
        <StatusDot status={project.status} showLabel />
      </div>

      {project.description && (
        <p className="text-gray-500 text-sm mb-6">{project.description}</p>
      )}

      {/* ── NEW PROJECT: Onboarding Flow ──────────────────────────── */}
      {isNewProject && (
        <div className="mt-6">
          <ProjectOnboarding project={project} />
        </div>
      )}

      {/* ── EXISTING PROJECT: Stats + Missions ───────────────────── */}
      {!isNewProject && (
        <>
          {/* Quick stats as inline badges */}
          <div className="flex items-center gap-3 mb-8 mt-1">
            <StatBadge value={project.total_missions} label="missions" />
            <StatBadge value={project.total_findings} label="findings" />
            <StatBadge value={reportsCount} label="reports" />
          </div>

          {/* New Mission */}
          <div className="mb-8">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              New Mission
            </h2>
            <form onSubmit={handleCreateMission} className="flex gap-3">
              <input
                type="text"
                value={missionInput}
                onChange={(e) => setMissionInput(e.target.value)}
                placeholder="Describe what you want to research..."
                className="flex-1 glass-card rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 focus:ring-1 focus:ring-emerald-500/20 transition-all duration-[180ms]"
              />
              <button
                type="submit"
                disabled={submitting || !missionInput.trim()}
                className="px-5 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-all duration-[180ms] whitespace-nowrap"
              >
                {submitting ? "Starting..." : "Start Research"}
              </button>
            </form>
          </div>

          {/* Missions list */}
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Missions
            </h2>
            <div className="space-y-1.5">
              {missions.map((mission) => (
                <button
                  key={mission.id}
                  onClick={() => router.push(`/missions/${mission.id}`)}
                  onMouseEnter={() => router.prefetch(`/missions/${mission.id}`)}
                  className="w-full text-left glass-card border border-gray-800/40 rounded-xl px-4 py-3 hover:border-gray-700/50 transition-colors flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <StatusDot status={mission.status} />
                    <p className="text-gray-100 text-sm font-medium truncate group-hover:text-white transition-colors">
                      {mission.name}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-600 flex-shrink-0 ml-4">
                    <span>{mission.findings_count} findings</span>
                    <span className="w-16 text-right">{formatDate(mission.created_at)}</span>
                    <svg className="w-4 h-4 text-gray-700 group-hover:text-gray-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
