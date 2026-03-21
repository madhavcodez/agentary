"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchProject, fetchMissions, fetchFindings, fetchReports, createMission } from "@/lib/api";
import type { Project, Mission, Finding, Report } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  draft: "text-gray-400 bg-gray-400/10 border-gray-400/20",
  queued: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  running: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  paused: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  completed: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  failed: "text-red-400 bg-red-400/10 border-red-400/20",
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

type Tab = "missions" | "findings" | "reports";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("missions");
  const [loading, setLoading] = useState(true);
  const [showMissionForm, setShowMissionForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [missionForm, setMissionForm] = useState({ name: "", objective: "", mission_type: "research" });

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
      setReports(data);
    } catch {
      setReports([]);
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
    if (!missionForm.name.trim()) return;
    setSubmitting(true);
    try {
      await createMission({
        project_id: id,
        name: missionForm.name.trim(),
        objective: missionForm.objective.trim() || undefined,
        mission_type: missionForm.mission_type,
      });
      setMissionForm({ name: "", objective: "", mission_type: "research" });
      setShowMissionForm(false);
      await loadMissions();
      await loadProject();
    } catch {
      // silently handle
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
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "missions", label: "Missions" },
    { key: "findings", label: "Findings" },
    { key: "reports", label: "Reports" },
  ];

  return (
    <div className="max-w-6xl mx-auto px-8 py-8">
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-100 tracking-tight">{project.name}</h1>
            <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_COLORS[project.status] ?? STATUS_COLORS.draft}`}>
              {project.status}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full border ${TYPE_COLORS[project.project_type] ?? TYPE_COLORS.custom}`}>
              {project.project_type.replace(/_/g, " ")}
            </span>
          </div>
          {project.description && (
            <p className="text-gray-400 text-sm mt-1">{project.description}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-5">
          <p className="text-sm text-gray-500 mb-1">Total Missions</p>
          <p className="text-2xl font-bold text-gray-100">{project.total_missions}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-5">
          <p className="text-sm text-gray-500 mb-1">Total Findings</p>
          <p className="text-2xl font-bold text-gray-100">{project.total_findings}</p>
        </div>
        <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-5">
          <p className="text-sm text-gray-500 mb-1">Reports Generated</p>
          <p className="text-2xl font-bold text-gray-100">{project.total_reports_generated}</p>
        </div>
      </div>

      <div className="flex items-center gap-1 border-b border-gray-800/50 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.key
                ? "text-emerald-400 border-emerald-400"
                : "text-gray-500 border-transparent hover:text-gray-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "missions" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-gray-100 font-semibold text-sm">Missions</h3>
            <button
              onClick={() => setShowMissionForm(!showMissionForm)}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium transition-colors"
            >
              New Mission
            </button>
          </div>

          {showMissionForm && (
            <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-5 mb-4">
              <form onSubmit={handleCreateMission} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">Mission Name</label>
                  <input
                    type="text"
                    value={missionForm.name}
                    onChange={(e) => setMissionForm({ ...missionForm, name: e.target.value })}
                    placeholder="e.g. Competitor Pricing Analysis"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">Objective</label>
                  <textarea
                    value={missionForm.objective}
                    onChange={(e) => setMissionForm({ ...missionForm, objective: e.target.value })}
                    placeholder="What should this mission accomplish?"
                    rows={2}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400/50 transition-colors resize-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">Mission Type</label>
                  <select
                    value={missionForm.mission_type}
                    onChange={(e) => setMissionForm({ ...missionForm, mission_type: e.target.value })}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-emerald-400/50 transition-colors"
                  >
                    {MISSION_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-3 pt-1">
                  <button
                    type="submit"
                    disabled={submitting || !missionForm.name.trim()}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    {submitting ? "Creating..." : "Create Mission"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowMissionForm(false)}
                    className="px-5 py-2 text-gray-400 hover:text-gray-300 text-sm font-medium transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {missions.length === 0 ? (
            <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-10 text-center">
              <p className="text-gray-400 text-sm">No missions yet.</p>
              <p className="text-gray-600 text-xs mt-1">Create a mission to start gathering intelligence.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {missions.map((mission) => (
                <button
                  key={mission.id}
                  onClick={() => router.push(`/missions/${mission.id}`)}
                  className="w-full text-left bg-gray-900 border border-gray-800/50 rounded-xl p-4 hover:border-gray-700/50 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-gray-100 text-sm font-medium truncate">{mission.name}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full border whitespace-nowrap ${STATUS_COLORS[mission.status] ?? STATUS_COLORS.draft} ${mission.status === "running" ? "animate-pulse" : ""}`}>
                          {mission.status}
                        </span>
                      </div>
                      {mission.objective && (
                        <p className="text-gray-500 text-xs truncate max-w-md">{mission.objective}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-5 text-xs text-gray-600 flex-shrink-0 ml-4">
                    <span>{mission.findings_count} findings</span>
                    <span className={confidenceColor(mission.confidence_score)}>
                      {mission.confidence_score !== null ? `${Math.round(mission.confidence_score * 100)}%` : "--"}
                    </span>
                    <span>{formatDate(mission.created_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "findings" && (
        <div>
          {findings.length === 0 ? (
            <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-10 text-center">
              <p className="text-gray-400 text-sm">No findings yet.</p>
              <p className="text-gray-600 text-xs mt-1">Run missions to discover findings.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {findings.map((finding) => (
                <div
                  key={finding.id}
                  className="bg-gray-900 border border-gray-800/50 rounded-xl p-5"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="text-gray-100 text-sm font-medium truncate pr-2">{finding.title}</h4>
                    {finding.confidence !== null && (
                      <span className={`text-xs font-medium whitespace-nowrap ${confidenceColor(finding.confidence)}`}>
                        {Math.round(finding.confidence * 100)}%
                      </span>
                    )}
                  </div>
                  {finding.content && (
                    <p className="text-gray-500 text-xs line-clamp-3 mb-3">{finding.content}</p>
                  )}
                  <div className="flex items-center gap-3 text-xs text-gray-600">
                    {finding.source_type && <span>{finding.source_type}</span>}
                    {finding.source_url && (
                      <a
                        href={finding.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-emerald-400/70 hover:text-emerald-400 truncate max-w-[200px]"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {finding.source_url}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "reports" && (
        <div>
          {reports.length === 0 ? (
            <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-10 text-center">
              <p className="text-gray-400 text-sm">No reports yet.</p>
              <p className="text-gray-600 text-xs mt-1">Generate reports from your mission findings.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {reports.map((report) => (
                <div
                  key={report.id}
                  className="bg-gray-900 border border-gray-800/50 rounded-xl p-4 flex items-center justify-between"
                >
                  <div>
                    <p className="text-gray-100 text-sm font-medium">{report.title}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                      <span>{report.report_type.replace(/_/g, " ")}</span>
                      <span className={`px-1.5 py-0.5 rounded border ${STATUS_COLORS[report.status] ?? STATUS_COLORS.draft}`}>
                        {report.status}
                      </span>
                    </div>
                  </div>
                  <span className="text-xs text-gray-600">{formatDate(report.created_at)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
