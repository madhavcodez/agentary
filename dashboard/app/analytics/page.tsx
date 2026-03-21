"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchProjects,
  fetchMissions,
  fetchFindings,
  fetchReports,
  fetchExpertAgents,
} from "@/lib/api";
import type { Mission, ExpertAgent } from "@/lib/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const STATUS_DOT: Record<string, string> = {
  completed: "bg-emerald-400",
  active: "bg-indigo-400 animate-pulse",
  running: "bg-indigo-400 animate-pulse",
  pending: "bg-amber-400",
  failed: "bg-red-400",
};

export default function AnalyticsPage() {
  const [stats, setStats] = useState({
    projects: 0,
    missions: 0,
    findings: 0,
    reports: 0,
  });
  const [recentMissions, setRecentMissions] = useState<Mission[]>([]);
  const [agents, setAgents] = useState<ExpertAgent[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    const results = await Promise.allSettled([
      fetchProjects(),
      fetchMissions(),
      fetchFindings(),
      fetchReports(),
      fetchExpertAgents(),
    ]);

    let projectCount = 0;
    if (results[0].status === "fulfilled") {
      projectCount = (results[0].value as unknown[]).length;
    }

    let missionList: Mission[] = [];
    if (results[1].status === "fulfilled") {
      missionList = results[1].value as Mission[];
    }

    let findingsCount = 0;
    if (results[2].status === "fulfilled") {
      findingsCount = (results[2].value as unknown[]).length;
    }

    let reportsCount = 0;
    if (results[3].status === "fulfilled") {
      reportsCount = (results[3].value as unknown[]).length;
    }

    if (results[4].status === "fulfilled") {
      setAgents(results[4].value as ExpertAgent[]);
    }

    setStats({
      projects: projectCount,
      missions: missionList.length,
      findings: findingsCount,
      reports: reportsCount,
    });

    // Most recent 10 missions
    const sorted = [...missionList].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    setRecentMissions(sorted.slice(0, 10));

    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const statCards = [
    { label: "Total Projects", value: stats.projects, color: "text-indigo-400" },
    { label: "Total Missions", value: stats.missions, color: "text-emerald-400" },
    { label: "Total Findings", value: stats.findings, color: "text-cyan-400" },
    { label: "Total Reports", value: stats.reports, color: "text-amber-400" },
  ];

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-8">
        <div className="text-center py-20 text-gray-500 text-sm">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 space-y-8">
      <h1 className="text-2xl font-bold text-gray-100">Analytics</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((s) => (
          <div
            key={s.label}
            className="bg-gray-900 border border-gray-800/50 rounded-xl px-5 py-4 text-center"
          >
            <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-gray-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Recent Missions */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200">Recent Missions</h2>
        </div>
        <div className="divide-y divide-gray-800/50">
          {recentMissions.length === 0 && (
            <div className="px-6 py-8 text-center text-sm text-gray-500">
              No missions yet
            </div>
          )}
          {recentMissions.map((m) => (
            <div key={m.id} className="px-6 py-3.5 flex items-center gap-3">
              <div
                className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[m.status] ?? "bg-gray-500"}`}
              />
              <div className="min-w-0 flex-1">
                <div className="text-sm text-gray-200 truncate">{m.name}</div>
                <div className="text-xs text-gray-500 mt-0.5 capitalize">{m.status}</div>
              </div>
              <div className="text-xs text-gray-500 shrink-0">
                {m.findings_count} findings
              </div>
              <div className="text-xs text-gray-500 shrink-0">
                {formatDate(m.created_at)}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Expert Agents */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200">Expert Agents</h2>
        </div>
        <div className="divide-y divide-gray-800/50">
          {agents.length === 0 && (
            <div className="px-6 py-8 text-center text-sm text-gray-500">
              No agents available
            </div>
          )}
          {agents.map((a) => (
            <div key={a.id} className="px-6 py-3.5 flex items-center gap-3">
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 ${
                  a.is_active
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-gray-800 text-gray-500"
                }`}
              >
                {a.icon ?? a.name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm text-gray-200">{a.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">{a.specialty}</div>
              </div>
              <div
                className={`text-xs px-2 py-0.5 rounded-full ${
                  a.is_active
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-gray-800 text-gray-500"
                }`}
              >
                {a.is_active ? "Active" : "Inactive"}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
