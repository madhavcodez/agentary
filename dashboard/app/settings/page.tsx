"use client";

import { useCallback, useEffect, useState } from "react";

const INTEGRATIONS = [
  { key: "gemini", name: "Gemini", desc: "LLM & search" },
  { key: "exa", name: "Exa", desc: "Web search" },
  { key: "twilio", name: "Twilio", desc: "Voice calls" },
  { key: "resend", name: "Resend", desc: "Email" },
  { key: "google_places", name: "Google Places", desc: "Location data" },
  { key: "yelp", name: "Yelp", desc: "Business data" },
  { key: "crunchbase", name: "Crunchbase", desc: "Company data" },
  { key: "zillow", name: "Zillow", desc: "Real estate data" },
  { key: "web_scraper", name: "Web Scraper", desc: "HTML extraction" },
];

const DATA_SERVICES = [
  { key: "postgres", name: "PostgreSQL", desc: "Primary database" },
  { key: "redis", name: "Redis", desc: "Cache & pub/sub" },
  { key: "qdrant", name: "Qdrant", desc: "Vector search" },
];

interface HealthData {
  status: string;
  checks: Record<string, string>;
  circuit_breakers?: Record<string, { state: string; fail_count: number; fail_max: number }>;
}

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/health");
      const data = await res.json();
      setHealth(data);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const isDataOk = (key: string) => health?.checks?.[key] === "ok";
  const isIntegrationOk = (key: string) => health?.circuit_breakers?.[key]?.state === "closed";
  const systemOk = health?.status === "ok";
  const allDataOk = DATA_SERVICES.every((s) => isDataOk(s.key));
  const integrationCount = INTEGRATIONS.filter((s) => isIntegrationOk(s.key)).length;

  return (
    <div className="max-w-3xl mx-auto px-8 py-8 space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Settings</h1>

      {/* Platform */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800/50">
          <h2 className="text-sm font-semibold text-gray-200">Platform</h2>
        </div>
        <div className="px-6 py-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Version</span>
            <span className="text-sm font-mono text-gray-300">0.2.0</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">System Status</span>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${error ? "bg-red-400" : systemOk ? "bg-emerald-400" : "bg-amber-400"}`} />
              <span className={`text-sm font-medium ${error ? "text-red-400" : systemOk ? "text-emerald-400" : "text-amber-400"}`}>
                {error ? "Unreachable" : systemOk ? "Operational" : "Degraded"}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Data Infrastructure */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800/50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Infrastructure</h2>
          <span className={`text-xs ${allDataOk ? "text-emerald-400" : "text-amber-400"}`}>
            {allDataOk ? "All connected" : "Checking..."}
          </span>
        </div>
        <div className="divide-y divide-gray-800/30">
          {DATA_SERVICES.map((svc) => {
            const ok = isDataOk(svc.key);
            return (
              <div key={svc.key} className="px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${ok ? "bg-emerald-400" : "bg-gray-600"}`} />
                  <div>
                    <span className="text-sm text-gray-200">{svc.name}</span>
                    <span className="text-xs text-gray-600 ml-2">{svc.desc}</span>
                  </div>
                </div>
                <span className={`text-xs font-medium ${ok ? "text-emerald-400" : "text-gray-500"}`}>
                  {ok ? "Connected" : "Offline"}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      {/* Integrations */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800/50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Integrations</h2>
          <span className="text-xs text-gray-500">
            {integrationCount}/{INTEGRATIONS.length} active
          </span>
        </div>
        <div className="divide-y divide-gray-800/30">
          {INTEGRATIONS.map((svc) => {
            const ok = isIntegrationOk(svc.key);
            const cb = health?.circuit_breakers?.[svc.key];
            return (
              <div key={svc.key} className="px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${ok ? "bg-emerald-400" : "bg-gray-600"}`} />
                  <div>
                    <span className="text-sm text-gray-200">{svc.name}</span>
                    <span className="text-xs text-gray-600 ml-2">{svc.desc}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {cb && cb.fail_count > 0 && (
                    <span className="text-xs text-amber-400">{cb.fail_count} failures</span>
                  )}
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    ok ? "bg-emerald-500/10 text-emerald-400" : "bg-gray-800 text-gray-500"
                  }`}>
                    {ok ? "Ready" : "Inactive"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* About */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl p-6">
        <p className="text-sm text-gray-500">
          Agentary v0.2.0 — Autonomous research & intelligence platform.
          Deploy AI agents that research, analyze, and report automatically.
        </p>
      </section>
    </div>
  );
}
