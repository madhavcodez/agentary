"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { fetchMissions, fetchProjects } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { Mission, Project } from "@/lib/types";

const STATUS_FILTERS = ["all", "draft", "running", "completed", "failed"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

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

export default function MissionsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<StatusFilter>("all");

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
      toast("Failed to load missions", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

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

  const filterCounts = useMemo(() => {
    const counts: Record<string, number> = { all: missions.length };
    for (const m of missions) {
      counts[m.status] = (counts[m.status] ?? 0) + 1;
    }
    return counts;
  }, [missions]);

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-100 tracking-tight">Missions</h1>
        <p className="text-gray-500 mt-2">
          Operations overview for all mission runs, outcomes, and execution states.
        </p>
      </div>

      {/* Filter pills */}
      <div className="flex items-center gap-2 mb-6">
        {STATUS_FILTERS.map((filter) => {
          const count = filterCounts[filter] ?? 0;
          const isActive = activeFilter === filter;
          return (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors capitalize ${
                isActive
                  ? "bg-emerald-400/15 text-emerald-400 border border-emerald-400/30"
                  : "bg-gray-900 text-gray-500 border border-gray-800/50 hover:text-gray-300 hover:border-gray-700/50"
              }`}
            >
              {filter}
              {count > 0 && (
                <span className={`ml-1.5 ${isActive ? "text-emerald-400/70" : "text-gray-700"}`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-gray-700 border-t-emerald-400 rounded-full animate-spin" />
        </div>
      ) : filteredMissions.length === 0 ? (
        <div className="bg-[#0b1220] border border-white/10 rounded-2xl p-12 text-center">
          <p className="text-gray-400 mb-2">
            {activeFilter === "all" ? "No missions yet" : `No ${activeFilter} missions`}
          </p>
          <button
            onClick={() => router.push("/projects")}
            className="text-emerald-400 hover:text-emerald-300 text-sm transition-colors"
          >
            {activeFilter === "all"
              ? "Go to a project to create your first mission"
              : "Try a different filter"}
          </button>
        </div>
      ) : (
        <div className="space-y-1.5">
          {filteredMissions.map((mission) => (
            <button
              key={mission.id}
              onClick={() => router.push(`/missions/${mission.id}`)}
              className="w-full text-left bg-[#0b1220] border border-white/10 rounded-2xl px-4 py-3 hover:border-white/20 transition-colors flex items-center justify-between group"
            >
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot(mission.status)}`} role="img" aria-label={`Status: ${mission.status}`} />
                <div className="min-w-0">
                  <p className="text-gray-100 text-sm font-medium truncate group-hover:text-white transition-colors">
                    {mission.name}
                  </p>
                  <p className="text-gray-600 text-xs truncate">
                    {projectMap[mission.project_id] ?? "Unknown project"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-600 flex-shrink-0 ml-4">
                <span>{mission.findings_count} findings</span>
                <span className="w-14 text-right">{formatDate(mission.created_at)}</span>
                <svg className="w-4 h-4 text-gray-700 group-hover:text-gray-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
