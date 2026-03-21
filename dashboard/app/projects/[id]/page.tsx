"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  fetchProject,
  fetchMissions,
  fetchFindings,
  fetchReports,
  createMission,
} from "@/lib/api";
import type { Project, Mission, Finding } from "@/lib/types";

const TYPE_ICONS: Record<string, string> = {
  real_estate: "🏠",
  competitive_intel: "🔍",
  due_diligence: "📋",
  data_extraction: "📊",
  market_research: "📈",
  local_business: "🏪",
  custom: "⚙️",
};

function statusDot(status: string): string {
  switch (status) {
    case "running":
      return "bg-emerald-400 animate-pulse";
    case "completed":
      return "bg-emerald-400";
    case "failed":
      return "bg-red-400";
    default:
      return "bg-gray-500";
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function confidenceBadge(confidence: number | null): string {
  if (confidence === null) return "text-gray-600";
  if (confidence >= 0.8) return "text-emerald-400";
  if (confidence >= 0.5) return "text-amber-400";
  return "text-red-400";
}

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
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
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadMissions = useCallback(async () => {
    try {
      const data = await fetchMissions({ project_id: id });
      setMissions(data);
    } catch {
      setMissions([]);
    }
  }, [id]);

  const loadFindings = useCallback(async () => {
    try {
      const data = await fetchFindings({ project_id: id });
      setFindings(data);
    } catch {
      setFindings([]);
    }
  }, [id]);

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
    loadFindings();
    loadReports();
  }, [loadProject, loadMissions, loadFindings, loadReports]);

  const handleCreateMission = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = missionInput.trim();
    if (!name) return;
    setSubmitting(true);
    try {
      await createMission({
        project_id: id,
        name,
        mission_type: "research",
      });
      setMissionInput("");
      await loadMissions();
      await loadProject();
    } catch {
      // error handled silently
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-gray-700 border-t-emerald-400 rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-12 text-center">
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
  const recentFindings = findings.slice(0, 5);

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
      <div className="flex items-center gap-3 mb-6">
        <span className="text-2xl">{icon}</span>
        <h1 className="text-2xl font-bold text-gray-100 tracking-tight">
          {project.name}
        </h1>
        <span className="text-xs px-2.5 py-0.5 rounded-full border border-gray-700 text-gray-400 capitalize">
          {project.project_type.replace(/_/g, " ")}
        </span>
        <span className="flex items-center gap-1.5 text-xs text-gray-400">
          <span className={`w-2 h-2 rounded-full ${statusDot(project.status)}`} />
          {project.status}
        </span>
      </div>

      {project.description && (
        <p className="text-gray-500 text-sm mb-6 -mt-2">{project.description}</p>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4 mb-10">
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-5">
          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Missions</p>
          <p className="text-2xl font-bold text-gray-100">{project.total_missions}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-5">
          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Findings</p>
          <p className="text-2xl font-bold text-gray-100">{project.total_findings}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-5">
          <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Reports</p>
          <p className="text-2xl font-bold text-gray-100">{reportsCount}</p>
        </div>
      </div>

      {/* New Mission */}
      <div className="mb-10">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          New Mission
        </h2>
        <form onSubmit={handleCreateMission} className="flex gap-3">
          <input
            type="text"
            value={missionInput}
            onChange={(e) => setMissionInput(e.target.value)}
            placeholder="Describe what you want to research..."
            className="flex-1 bg-gray-900 border border-gray-800/50 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 transition-colors"
          />
          <button
            type="submit"
            disabled={submitting || !missionInput.trim()}
            className="px-5 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-colors whitespace-nowrap"
          >
            {submitting ? "Starting..." : "Start Research"}
          </button>
        </form>
      </div>

      {/* Missions list */}
      <div className="mb-10">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Missions
        </h2>
        {missions.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-8 text-center">
            <p className="text-gray-500 text-sm">No missions yet. Create one above to get started.</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {missions.map((mission) => (
              <button
                key={mission.id}
                onClick={() => router.push(`/missions/${mission.id}`)}
                className="w-full text-left bg-gray-900 border border-gray-800/50 rounded-xl px-4 py-3 hover:border-gray-700/50 transition-colors flex items-center justify-between group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot(mission.status)}`} />
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
        )}
      </div>

      {/* Recent Findings */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Recent Findings
        </h2>
        {recentFindings.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-8 text-center">
            <p className="text-gray-500 text-sm">No findings yet. Run a mission to discover findings.</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {recentFindings.map((finding) => (
              <div
                key={finding.id}
                className="bg-gray-900 border border-gray-800/50 rounded-xl px-4 py-3 flex items-center justify-between"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-gray-100 text-sm font-medium truncate">{finding.title}</p>
                  {finding.content && (
                    <p className="text-gray-600 text-xs truncate mt-0.5 max-w-xl">{finding.content}</p>
                  )}
                </div>
                <div className="flex items-center gap-4 text-xs flex-shrink-0 ml-4">
                  {finding.confidence !== null && (
                    <span className={`font-medium ${confidenceBadge(finding.confidence)}`}>
                      {Math.round(finding.confidence * 100)}%
                    </span>
                  )}
                  {finding.source_type && (
                    <span className="text-gray-600">{finding.source_type}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
