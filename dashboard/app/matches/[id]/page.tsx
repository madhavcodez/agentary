"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchMatch,
  fetchDossier,
  generateDossier,
  updateMatchStatus,
  createContact,
  createCampaign,
} from "@/lib/api";
import type { Match, Dossier } from "@/lib/types";
import ScoreBadge from "@/components/ScoreBadge";
import DossierView from "@/components/DossierView";

function validatePhone(phone: string): boolean {
  return /^\+[1-9]\d{1,14}$/.test(phone);
}

export default function MatchDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [match, setMatch] = useState<Match | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [loading, setLoading] = useState(true);
  const [dossierLoading, setDossierLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Outreach form state
  const [showOutreach, setShowOutreach] = useState(false);
  const [outreachName, setOutreachName] = useState("");
  const [outreachPhone, setOutreachPhone] = useState("");
  const [outreachError, setOutreachError] = useState<string | null>(null);
  const [outreachLoading, setOutreachLoading] = useState(false);

  const loadMatch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const m = await fetchMatch(id);
      setMatch(m);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch match");
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadDossier = useCallback(async () => {
    setDossierLoading(true);
    try {
      const d = await fetchDossier(id);
      setDossier(d);
    } catch {
      // Dossier not found is expected
    } finally {
      setDossierLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadMatch();
    loadDossier();
  }, [loadMatch, loadDossier]);

  async function handleGenerateDossier() {
    setGenerating(true);
    try {
      const d = await generateDossier(id);
      setDossier(d);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate dossier"
      );
    } finally {
      setGenerating(false);
    }
  }

  async function handleAction(status: string) {
    setActionLoading(status);
    try {
      const updated = await updateMatchStatus(id, status);
      setMatch(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update match status"
      );
    } finally {
      setActionLoading(null);
    }
  }

  async function handleStartOutreach() {
    setOutreachError(null);

    if (!outreachPhone.trim()) {
      setOutreachError("Phone number is required");
      return;
    }
    if (!validatePhone(outreachPhone.trim())) {
      setOutreachError("Phone must be E.164 format (e.g., +12125551234)");
      return;
    }

    setOutreachLoading(true);
    try {
      const company = match?.opportunity?.company ?? "Unknown";
      const contact = await createContact({
        company,
        name: outreachName.trim() || undefined,
        phone: outreachPhone.trim(),
        source: "outreach",
        opportunity_id: match?.opportunity_id,
      });
      await createCampaign({
        match_id: id,
        contact_id: contact.id,
      });
      router.push("/calls");
    } catch (err) {
      setOutreachError(
        err instanceof Error ? err.message : "Failed to create campaign"
      );
    } finally {
      setOutreachLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl">
        <div className="text-center py-16">
          <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading match...</p>
        </div>
      </div>
    );
  }

  if (error && !match) {
    return (
      <div className="max-w-4xl">
        <Link
          href="/matches"
          className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors mb-6"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Back to Matches
        </Link>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!match) return null;

  const company = match.opportunity?.company ?? "Unknown Company";
  const title = match.opportunity?.title ?? "Unknown Position";

  return (
    <div className="max-w-4xl">
      <Link
        href="/matches"
        className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to Matches
      </Link>

      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">{title}</h1>
            <p className="text-base text-gray-400 mt-1">{company}</p>
          </div>
          <ScoreBadge score={match.composite_score} size="lg" />
        </div>

        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400">
          <span
            className={`capitalize font-medium ${
              match.status === "approved"
                ? "text-emerald-400"
                : match.status === "rejected"
                  ? "text-red-400"
                  : match.status === "saved"
                    ? "text-blue-400"
                    : "text-gray-400"
            }`}
          >
            {match.status}
          </span>
          <span className="text-gray-700">|</span>
          <span>
            Filter:{" "}
            {match.hard_filter_pass === "pass" ? (
              <span className="text-emerald-400">Passed</span>
            ) : (
              <span className="text-red-400">{match.hard_filter_pass}</span>
            )}
          </span>
          <span className="text-gray-700">|</span>
          <span className="text-gray-500">
            {new Date(match.created_at).toLocaleDateString()}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-5 pt-5 border-t border-gray-800">
          {["approved", "saved", "rejected"].map((status) => {
            const isActive = match.status === status;
            const colors: Record<string, string> = {
              approved: isActive
                ? "bg-emerald-600 text-white"
                : "bg-gray-800 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/10",
              saved: isActive
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-blue-400 border-blue-500/20 hover:bg-blue-500/10",
              rejected: isActive
                ? "bg-red-600 text-white"
                : "bg-gray-800 text-red-400 border-red-500/20 hover:bg-red-500/10",
            };
            return (
              <button
                key={status}
                onClick={() => handleAction(status)}
                disabled={actionLoading !== null}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors capitalize ${colors[status]} ${
                  actionLoading === status ? "opacity-50" : ""
                }`}
              >
                {actionLoading === status ? "..." : status}
              </button>
            );
          })}

          {match.opportunity?.url && (
            <a
              href={match.opportunity.url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
              </svg>
              Apply
            </a>
          )}
        </div>
      </div>

      {/* Score Breakdown */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
          Score Breakdown
        </h2>
        <div className="grid grid-cols-3 gap-6">
          <ScoreDetail
            label="Composite"
            score={match.composite_score}
            description="Overall match quality"
          />
          <ScoreDetail
            label="Semantic"
            score={match.semantic_score}
            description="Skills and experience alignment"
          />
          <ScoreDetail
            label="LLM"
            score={match.llm_score}
            description="AI-assessed fit quality"
          />
        </div>

        {match.rationale && (
          <div className="mt-6 pt-5 border-t border-gray-800">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">
              Rationale
            </h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              {match.rationale}
            </p>
          </div>
        )}
      </div>

      {/* Start Outreach */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              Outreach
            </h2>
            <p className="text-xs text-gray-500 mt-1">
              Create a campaign to reach out about this opportunity
            </p>
          </div>
          {!showOutreach && (
            <button
              onClick={() => setShowOutreach(true)}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
              </svg>
              Start Outreach
            </button>
          )}
        </div>

        {showOutreach && (
          <div className="border-t border-gray-800 pt-4">
            {outreachError && (
              <div className="mb-4 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                <p className="text-xs text-red-400">{outreachError}</p>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Contact Name
                </label>
                <input
                  type="text"
                  value={outreachName}
                  onChange={(e) => setOutreachName(e.target.value)}
                  placeholder="Jane Smith"
                  className="w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Phone Number <span className="text-red-400">*</span>
                </label>
                <input
                  type="tel"
                  value={outreachPhone}
                  onChange={(e) => setOutreachPhone(e.target.value)}
                  placeholder="+12125551234"
                  className="w-full px-3 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors font-mono"
                />
                <p className="text-xs text-gray-600 mt-1">E.164 format: +[country code][number]</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleStartOutreach}
                disabled={outreachLoading}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {outreachLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-emerald-300 border-t-transparent rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                    </svg>
                    Create Campaign
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  setShowOutreach(false);
                  setOutreachError(null);
                  setOutreachName("");
                  setOutreachPhone("");
                }}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 font-medium rounded-lg transition-colors"
              >
                Cancel
              </button>
              <Link
                href="/contacts"
                className="ml-auto text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Or add from Contacts &rarr;
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Dossier */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-200">
            Research Dossier
          </h2>
          <button
            onClick={handleGenerateDossier}
            disabled={generating}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {generating ? (
              <>
                <div className="w-4 h-4 border-2 border-gray-600 border-t-indigo-400 rounded-full animate-spin" />
                Generating...
              </>
            ) : dossier ? (
              "Regenerate Dossier"
            ) : (
              "Generate Dossier"
            )}
          </button>
        </div>

        {dossierLoading ? (
          <div className="text-center py-8">
            <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
            <p className="text-sm text-gray-500 mt-3">Loading dossier...</p>
          </div>
        ) : dossier ? (
          <DossierView contentMd={dossier.content_md} />
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <svg className="w-10 h-10 mx-auto text-gray-700 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <p className="text-sm text-gray-500">No dossier generated yet.</p>
            <p className="text-xs text-gray-600 mt-1">
              Click &quot;Generate Dossier&quot; to create a detailed research report.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreDetail({
  label,
  score,
  description,
}: {
  label: string;
  score: number;
  description: string;
}) {
  const rounded = Math.round(score);
  const barColor =
    rounded >= 70
      ? "bg-emerald-500"
      : rounded >= 40
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <ScoreBadge score={score} size="sm" />
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${Math.min(100, rounded)}%` }}
        />
      </div>
      <p className="text-xs text-gray-600 mt-1.5">{description}</p>
    </div>
  );
}
