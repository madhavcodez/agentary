"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api";
import type { HealthCheck } from "@/lib/types";

const INTEGRATIONS = [
  { key: "gemini", name: "Gemini", envHint: "AIza...3_Yk" },
  { key: "exa", name: "Exa", envHint: "exa-...x9f2" },
  { key: "twilio", name: "Twilio", envHint: "AC...d4e1" },
  { key: "resend", name: "Resend", envHint: "re_...kL9m" },
  { key: "google_places", name: "Google Places", envHint: "AIza...pQ7x" },
  { key: "yelp", name: "Yelp", envHint: "yelp...rT3w" },
  { key: "crunchbase", name: "Crunchbase", envHint: "cb_...nM2j" },
  { key: "zillow", name: "Zillow", envHint: "zws-...hR4v" },
];

const DATA_SERVICES = [
  { key: "database", name: "PostgreSQL", icon: "DB" },
  { key: "redis", name: "Redis", icon: "RD" },
  { key: "qdrant", name: "Qdrant", icon: "QD" },
];

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <div
      className={`w-2 h-2 rounded-full shrink-0 ${ok ? "bg-emerald-400" : "bg-gray-500"}`}
    />
  );
}

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [healthError, setHealthError] = useState(false);

  const loadHealth = useCallback(async () => {
    try {
      const data = await fetchHealth();
      setHealth(data);
      setHealthError(false);
    } catch {
      setHealthError(true);
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  const checkStatus = (key: string): boolean => {
    if (!health?.checks) return false;
    const val = health.checks[key];
    if (!val) return false;
    return val === "ok" || val === "healthy" || val === "connected" || val === "up";
  };

  const systemOk = health?.status === "ok" || health?.status === "healthy";

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 space-y-8">
      <h1 className="text-2xl font-bold text-gray-100">Settings</h1>

      {/* Section 1 — Platform */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200">Platform</h2>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Version</span>
            <span className="text-sm font-mono text-gray-200">0.2.0</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">System Status</span>
            <div className="flex items-center gap-2">
              <StatusDot ok={systemOk} />
              <span className={`text-sm ${systemOk ? "text-emerald-400" : "text-gray-500"}`}>
                {healthError ? "Unreachable" : systemOk ? "Operational" : "Degraded"}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2 — Integrations */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200">Integrations</h2>
        </div>
        <div className="divide-y divide-gray-800/50">
          {INTEGRATIONS.map((svc) => {
            const ok = checkStatus(svc.key);
            return (
              <div
                key={svc.key}
                className="px-6 py-3.5 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <StatusDot ok={ok} />
                  <span className="text-sm text-gray-200">{svc.name}</span>
                </div>
                <span className="text-xs font-mono text-gray-500">{svc.envHint}</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* Section 3 — Data */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200">Data</h2>
        </div>
        <div className="divide-y divide-gray-800/50">
          {DATA_SERVICES.map((svc) => {
            const ok = checkStatus(svc.key);
            return (
              <div
                key={svc.key}
                className="px-6 py-3.5 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <StatusDot ok={ok} />
                  <span className="text-sm text-gray-200">{svc.name}</span>
                </div>
                <span
                  className={`text-xs ${ok ? "text-emerald-400" : "text-gray-500"}`}
                >
                  {ok ? "Connected" : "Unknown"}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      {/* Section 4 — About */}
      <section className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200">About</h2>
        </div>
        <div className="px-6 py-5">
          <p className="text-sm text-gray-400">
            Agentary v0.2.0 — Autonomous research & intelligence platform
          </p>
        </div>
      </section>
    </div>
  );
}
