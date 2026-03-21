"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { fetchMissions, fetchProjects, createMission } from "@/lib/api";
import type { Mission, Project } from "@/lib/types";

const STATUS_FILTERS = ["all", "draft", "running", "completed", "failed"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const STATUS_COLORS: Record<string, string> = {
  draft: "text-gray-400 bg-gray-400/10 border-gray-400/20",
  queued: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  running: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  paused: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  completed: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  failed: "text-red-400 bg-red-400/10 border-red-400/20",
};

const MISSION_TYPES = [
  { value: "research", label: "Research" },
  { value: "data_collection", label: "Data Collection" },
  { value: "competitive_analysis", label: "Competitive Analysis" },
  { value: "market_survey", label: "Market Survey" },
  { value: "due_diligence", label: "Due Diligence" },
  { value: "custom", label: "Custom" },
];

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function confidenceColor(confidence: number | null): string {
  if (confidence === null) return "text-gray-500";
  if (confidence >= 0.8) return "text-emerald-400";
  if (confidence >= 0.5) return "text-amber-400";
  return "text-red-400";
}

export default function MissionsPage() {
  const router = useRouter();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<StatusFilter>("all");
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ project_id: "", name: "", objective: "", mission_type: "research" });

  const projectMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const p of projects) {
      map[p.id] = p.name;
    }
    return map;
  }, [projects]);

  const loadMissions = useCallback(async () => {
    try {
      const data = await fetchMissions();
      setMissions(data);
    } catch {
      setMissions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProjects = useCallback(async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch {
      setProjects([]);
    }
  }, []);

  useEffect(() => {
    loadMissions();
    loadProjects();
  }, [loadMissions, loadProjects]);

  const filteredMissions = useMemo(() => {
    if (activeFilter === "all") return missions;
    return missions.filter((m) => m.status === activeFilter);
  }, [missions, activeFilter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.project_id) return;
    setSubmitting(true);
    try {
      await createMission({
        project_id: form.project_id,
        name: form.name.trim(),
        objective: form.objective.trim() || undefined,
        mission_type: form.mission_type,
      });
      setForm({ project_id: "", name: "", objective: "", mission_type: "research" });
      setShowForm(false);
      await loadMissions();
    } catch {
      // silently handle
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-100 tracking-tight">Missions</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          New Mission
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-6 mb-6">
          <h3 className="text-gray-100 font-semibold mb-4">Create New Mission</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Project</label>
              <select
                value={form.project_id}
                onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-emerald-400/50 transition-colors"
              >
                <option value="">Select a project</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Mission Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Competitor Pricing Analysis"
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Objective</label>
              <textarea
                value={form.objective}
                onChange={(e) => setForm({ ...form, objective: e.target.value })}
                placeholder="What should this mission accomplish?"
                rows={2}
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 transition-colors resize-none"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Mission Type</label>
              <select
                value={form.mission_type}
                onChange={(e) => setForm({ ...form, mission_type: e.target.value })}
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-emerald-400/50 transition-colors"
              >
                {MISSION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={submitting || !form.name.trim() || !form.project_id}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
              >
                {submitting ? "Creating..." : "Create Mission"}
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

      <div className="flex items-center gap-1 border-b border-gray-800/50 mb-6">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter)}
            className={`px-4 py-2.5 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              activeFilter === filter
                ? "text-emerald-400 border-emerald-400"
                : "text-gray-500 border-transparent hover:text-gray-300"
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-gray-700 border-t-emerald-400 rounded-full animate-spin" />
        </div>
      ) : filteredMissions.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-12 text-center">
          <svg className="w-10 h-10 text-gray-700 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
          </svg>
          <p className="text-gray-400">
            {activeFilter === "all" ? "No missions yet" : `No ${activeFilter} missions`}
          </p>
          <p className="text-sm text-gray-600 mt-1">
            {activeFilter === "all"
              ? "Create a mission within a project to start researching."
              : "Try a different filter or create a new mission."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredMissions.map((mission) => (
            <button
              key={mission.id}
              onClick={() => router.push(`/missions/${mission.id}`)}
              className="w-full text-left bg-gray-900 border border-gray-800/50 rounded-xl p-4 hover:border-gray-700/50 transition-colors flex items-center justify-between"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <p className="text-gray-100 text-sm font-medium truncate">{mission.name}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full border whitespace-nowrap ${STATUS_COLORS[mission.status] ?? STATUS_COLORS.draft} ${mission.status === "running" ? "animate-pulse" : ""}`}>
                    {mission.status}
                  </span>
                </div>
                <p className="text-gray-600 text-xs">
                  {projectMap[mission.project_id] ?? "Unknown project"}
                </p>
              </div>
              <div className="flex items-center gap-5 text-xs text-gray-600 flex-shrink-0 ml-4">
                <span>{mission.findings_count} findings</span>
                <span className={confidenceColor(mission.confidence_score)}>
                  {mission.confidence_score !== null ? `${Math.round(mission.confidence_score * 100)}%` : "--"}
                </span>
                <span className="w-20 text-right">{formatDate(mission.created_at)}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
