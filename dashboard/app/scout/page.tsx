"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchProfile } from "@/lib/api";
import { useScoutWebSocket } from "@/lib/hooks/useScoutWebSocket";
import type { ScoutMode, Skill } from "@/lib/types";
import ScoutControls from "@/components/scout/ScoutControls";
import ScoutLog from "@/components/scout/ScoutLog";
import LiveJobCard from "@/components/scout/LiveJobCard";
import Spinner from "@/components/ui/Spinner";

export default function ScoutPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [activeSkills, setActiveSkills] = useState<string[]>([]);
  const [mode, setMode] = useState<ScoutMode>("rank_all");
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [profileError, setProfileError] = useState("");

  const scout = useScoutWebSocket();

  // Load profile skills on mount
  useEffect(() => {
    setLoadingProfile(true);
    fetchProfile()
      .then((profile) => {
        const profileSkills = profile.skills ?? [];
        setSkills(profileSkills);
        // Pre-select all skills
        setActiveSkills(profileSkills.map((s) => s.name));
      })
      .catch(() => {
        setProfileError("Could not load profile. Upload your resume first.");
      })
      .finally(() => setLoadingProfile(false));
  }, []);

  const handleToggleSkill = useCallback((name: string) => {
    setActiveSkills((prev) =>
      prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name],
    );
  }, []);

  const handleStart = useCallback(() => {
    scout.start(mode, activeSkills);
  }, [scout, mode, activeSkills]);

  if (loadingProfile) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-100">Live Scout</h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time job discovery, filtering, and AI scoring
          </p>
        </div>
        <div className="flex items-center justify-center py-20">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (profileError) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-100">Live Scout</h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time job discovery, filtering, and AI scoring
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <p className="text-sm text-gray-400">{profileError}</p>
          <a
            href="/"
            className="inline-block mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors"
          >
            Go to Profile
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Live Scout</h1>
        <p className="text-sm text-gray-400 mt-1">
          Real-time job discovery, filtering, and AI scoring
        </p>
      </div>

      {/* Controls bar */}
      <ScoutControls
        status={scout.status}
        mode={mode}
        onModeChange={setMode}
        skills={skills}
        activeSkills={activeSkills}
        onToggleSkill={handleToggleSkill}
        progress={scout.progress}
        onStart={handleStart}
        onPause={scout.pause}
        onResume={scout.resume}
        onCancel={scout.cancel}
        onReset={scout.reset}
      />

      {/* Split-view: log on left, results on right */}
      <div className="mt-4 grid grid-cols-1 lg:grid-cols-5 gap-4" style={{ minHeight: "calc(100vh - 320px)" }}>
        {/* Left panel — Scout Log (40%) */}
        <div className="lg:col-span-2 bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
            </svg>
            <span className="text-xs font-medium text-gray-400">Scout Log</span>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            <ScoutLog
              phases={scout.phases}
              status={scout.status}
              errorMessage={scout.errorMessage}
            />
          </div>
        </div>

        {/* Right panel — Live Results (60%) */}
        <div className="lg:col-span-3 bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
              </svg>
              <span className="text-xs font-medium text-gray-400">
                Live Results
              </span>
            </div>
            {scout.liveJobs.length > 0 && (
              <span className="text-xs text-gray-500">
                {scout.liveJobs.length} {scout.liveJobs.length === 1 ? "match" : "matches"}
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            {scout.liveJobs.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center px-6">
                  <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-gray-800/60 border border-gray-700/50 flex items-center justify-center">
                    <svg className="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </div>
                  <p className="text-sm text-gray-400">No results yet</p>
                  <p className="text-xs text-gray-600 mt-1">
                    {scout.status === "idle"
                      ? "Scored jobs will appear here as the scout runs"
                      : "Waiting for scoring to begin..."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {scout.liveJobs.map((job, idx) => (
                  <LiveJobCard key={job.match_id} job={job} index={idx} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
