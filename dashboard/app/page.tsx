"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [resume, setResume] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [scouting, setScouting] = useState(false);
  const [scoutResult, setScoutResult] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/profile`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setProfile)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function uploadResume() {
    if (!resume.trim()) return;
    setUploading(true);
    try {
      const res = await fetch(`${API}/profile/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_text: resume }),
      });
      if (res.ok) {
        const p = await res.json();
        setProfile(p);
        setResume("");
      }
    } finally {
      setUploading(false);
    }
  }

  async function runScout() {
    setScouting(true);
    setScoutResult(null);
    try {
      const res = await fetch(`${API}/ingest/run`, { method: "POST" });
      const data = await res.json();
      setScoutResult(`Ingested ${data.opportunities_ingested || 0} new opportunities`);
      // Auto-score after ingest
      await fetch(`${API}/matches/score`, { method: "POST" });
      setScoutResult((prev) => prev + " and scored all matches");
    } catch {
      setScoutResult("Scout failed — is the backend running?");
    } finally {
      setScouting(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-100">SecretAIRY</h1>
        <p className="text-sm text-gray-400 mt-1">
          Upload your resume, then let the AI scout opportunities and make calls on your behalf
        </p>
      </div>

      {/* Resume Upload */}
      {!profile && !loading && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-200 mb-3">Upload Your Resume</h2>
          <p className="text-sm text-gray-400 mb-4">
            Paste your resume text below. AI will extract your skills, experience, and preferences.
          </p>
          <textarea
            value={resume}
            onChange={(e) => setResume(e.target.value)}
            rows={10}
            placeholder="Paste your resume here..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:outline-none resize-none"
          />
          <button
            onClick={uploadResume}
            disabled={uploading || !resume.trim()}
            className="mt-3 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {uploading ? "Analyzing..." : "Upload & Analyze"}
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading profile...</p>
        </div>
      )}

      {/* Profile Display */}
      {profile && (
        <>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-100">{profile.name}</h2>
                {profile.location && <p className="text-sm text-gray-400 mt-0.5">{profile.location}</p>}
                {profile.email && <p className="text-xs text-gray-500 mt-0.5">{profile.email}</p>}
              </div>
              <button
                onClick={() => { setProfile(null); }}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                Re-upload
              </button>
            </div>

            {profile.summary && (
              <p className="text-sm text-gray-300 mb-4 leading-relaxed">{profile.summary}</p>
            )}

            {/* Skills */}
            {profile.skills?.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-2">Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {profile.skills.map((s: any) => (
                    <span key={s.id} className="px-2.5 py-1 bg-indigo-500/10 text-indigo-400 text-xs rounded-full border border-indigo-500/20">
                      {s.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Experience */}
            {profile.experiences?.length > 0 && (
              <div>
                <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-2">Experience</h3>
                <div className="space-y-2">
                  {profile.experiences.map((e: any) => (
                    <div key={e.id} className="bg-gray-800 rounded-lg p-3">
                      <p className="text-sm font-medium text-gray-200">{e.title}</p>
                      <p className="text-xs text-gray-400">{e.company}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Scout Action */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-gray-200 mb-2">Run Scout</h2>
            <p className="text-sm text-gray-400 mb-4">
              Search for new job opportunities from Greenhouse, Lever, and HN. Then auto-score matches against your profile.
            </p>
            <button
              onClick={runScout}
              disabled={scouting}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {scouting ? "Scouting..." : "Run Scout Now"}
            </button>
            {scoutResult && (
              <p className="text-sm text-emerald-400 mt-3">{scoutResult}</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
