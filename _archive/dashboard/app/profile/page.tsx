"use client";

import { useEffect, useState } from "react";
import { fetchProfile, uploadResume } from "@/lib/api";
import type { Profile } from "@/lib/types";
import ProfileForm from "@/components/ProfileForm";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const p = await fetchProfile();
        setProfile(p);
      } catch {
        // Profile not found is expected for new users
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!resumeText.trim()) return;

    setUploading(true);
    setError(null);
    setUploadSuccess(false);

    try {
      const p = await uploadResume(resumeText.trim());
      setProfile(p);
      setUploadSuccess(true);
      setResumeText("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to upload resume"
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-100">Profile</h1>
        <p className="text-sm text-gray-400 mt-1">
          Upload your resume to build your professional profile
        </p>
      </div>

      {/* Resume Upload */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
        <h2 className="text-base font-semibold text-gray-200 mb-4">
          {profile ? "Update Resume" : "Upload Resume"}
        </h2>

        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label
              htmlFor="resume-text"
              className="block text-sm font-medium text-gray-300 mb-1.5"
            >
              Paste your resume text
            </label>
            <textarea
              id="resume-text"
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="Paste the full text of your resume here..."
              rows={12}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors resize-y"
            />
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {uploadSuccess && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
              <p className="text-sm text-emerald-400">
                Resume uploaded and profile updated successfully.
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={uploading || !resumeText.trim()}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            {uploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
                Upload &amp; Parse Resume
              </>
            )}
          </button>
        </form>
      </div>

      {/* Parsed Profile */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading profile...</p>
        </div>
      ) : profile ? (
        <div>
          <h2 className="text-base font-semibold text-gray-200 mb-4">
            Parsed Profile
          </h2>
          <ProfileForm profile={profile} />
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-gray-700 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
          </svg>
          <p className="text-sm text-gray-500">No profile yet.</p>
          <p className="text-xs text-gray-600 mt-1">
            Upload your resume above to get started.
          </p>
        </div>
      )}
    </div>
  );
}
