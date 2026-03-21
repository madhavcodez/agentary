"use client";

import { useState, useEffect } from "react";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function JobDatabasePage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("limit", "20");
    if (search) params.set("search", search);
    if (source) params.set("source", source);

    fetch(`${API}/opportunities?${params}`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((d) => { setJobs(d.items || []); setTotal(d.total || 0); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page, search, source]);

  const totalPages = Math.ceil(total / 20);

  function truncate(text: string | null, len: number) {
    if (!text) return "";
    return text.length > len ? text.slice(0, len) + "..." : text;
  }

  return (
    <div className="max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Job Database</h1>
        <p className="text-sm text-gray-400 mt-1">{total} scraped opportunities</p>
      </div>

      {/* Search + Filter */}
      <div className="flex gap-3 mb-6">
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search jobs..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
        />
        <select
          value={source}
          onChange={(e) => { setSource(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-300 focus:border-indigo-500 focus:outline-none"
        >
          <option value="">All sources</option>
          <option value="greenhouse">Greenhouse</option>
          <option value="lever">Lever</option>
          <option value="hn_whos_hiring">HN</option>
        </select>
      </div>

      {loading ? (
        <div className="text-gray-500 text-sm py-12 text-center">Loading...</div>
      ) : jobs.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <p className="text-gray-400">No jobs found. Run Scout from the Profile page to ingest opportunities.</p>
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {jobs.map((job) => (
              <div key={job.id} className="bg-gray-900 border border-gray-800 rounded-lg px-5 py-4 hover:border-gray-700 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-100 truncate">{job.title}</h3>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs font-medium text-indigo-400">{job.company}</span>
                      {job.location && (
                        <span className="text-xs text-gray-500 truncate max-w-[200px]">{truncate(job.location, 40)}</span>
                      )}
                      <span className="px-1.5 py-0.5 bg-gray-800 text-gray-500 text-[10px] rounded uppercase">{job.source}</span>
                    </div>
                    {job.description && (
                      <p className="text-xs text-gray-500 mt-2 leading-relaxed">{truncate(job.description, 200)}</p>
                    )}
                  </div>
                  {job.url && (
                    <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-400 hover:text-indigo-300 whitespace-nowrap ml-4">
                      Apply
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 bg-gray-800 text-gray-400 text-xs rounded-lg disabled:opacity-30"
              >
                Prev
              </button>
              <span className="text-xs text-gray-500">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 bg-gray-800 text-gray-400 text-xs rounded-lg disabled:opacity-30"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
