"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function scoreColor(score: number) {
  if (score >= 70) return "bg-emerald-600 text-emerald-100";
  if (score >= 40) return "bg-amber-600 text-amber-100";
  return "bg-gray-600 text-gray-200";
}

export default function MatchesPage() {
  const [matches, setMatches] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/matches?limit=50`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((d) => { setMatches(d.items || []); setTotal(d.total || 0); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const scored = matches.filter((m) => m.composite_score > 0);

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Matches</h1>
        <p className="text-sm text-gray-400 mt-1">
          {scored.length} scored matches out of {total} total
        </p>
      </div>

      {loading ? (
        <div className="text-gray-500 text-sm py-12 text-center">Loading...</div>
      ) : scored.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <p className="text-gray-400">No scored matches yet.</p>
          <p className="text-sm text-gray-500 mt-1">Upload your resume and run Scout from the Profile page.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {scored.map((m) => (
            <div key={m.id} className="bg-gray-900 border border-gray-800 rounded-lg px-5 py-4 hover:border-gray-700 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${scoreColor(m.composite_score)}`}>
                      {Math.round(m.composite_score)}
                    </span>
                    <h3 className="text-sm font-semibold text-gray-100 truncate">
                      {m.opportunity?.title || "Unknown"}
                    </h3>
                  </div>
                  <p className="text-xs text-indigo-400 mt-1">{m.opportunity?.company || "Unknown"}</p>
                  {m.rationale && (
                    <p className="text-xs text-gray-500 mt-2 leading-relaxed">{m.rationale.slice(0, 200)}{m.rationale.length > 200 ? "..." : ""}</p>
                  )}
                </div>
                <Link
                  href={`/outreach?match=${m.id}`}
                  className="px-3 py-1.5 bg-indigo-600/20 text-indigo-400 text-xs rounded-lg hover:bg-indigo-600/30 whitespace-nowrap ml-4"
                >
                  Start Outreach
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
