"use client";

import { useState } from "react";
import { createMonitor } from "@/lib/api";

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

const MONITOR_TYPES = [
  { value: "web_content", label: "Web Content", desc: "Track changes on any web page" },
  { value: "api_data", label: "API Data", desc: "Monitor API endpoint responses" },
  { value: "price_tracker", label: "Price Tracker", desc: "Watch price changes" },
  { value: "listing_watcher", label: "Listing Watcher", desc: "Alert on new listings" },
  { value: "competitor_tracker", label: "Competitor Tracker", desc: "Track competitor changes" },
  { value: "custom", label: "Custom", desc: "Custom monitoring logic" },
];

const SCHEDULES = [
  { value: "*/5 * * * *", label: "Every 5 minutes" },
  { value: "*/15 * * * *", label: "Every 15 minutes" },
  { value: "0 * * * *", label: "Every hour" },
  { value: "0 */6 * * *", label: "Every 6 hours" },
  { value: "0 9 * * *", label: "Daily at 9 AM" },
  { value: "0 9 * * 1-5", label: "Weekdays at 9 AM" },
];

export default function MonitorCreateWizard({ onClose, onCreated }: Props) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [monitorType, setMonitorType] = useState("");
  const [url, setUrl] = useState("");
  const [schedule, setSchedule] = useState("0 * * * *");
  const [alertEmail, setAlertEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!name || !monitorType) return;
    setSubmitting(true);
    setError("");
    try {
      const channels = ["dashboard"];
      const recipients: string[] = [];
      if (alertEmail) {
        channels.push("email");
        recipients.push(alertEmail);
      }
      await createMonitor({
        name,
        monitor_type: monitorType,
        check_config: url ? { url } : {},
        alert_config: { channels, recipients },
        schedule_cron: schedule,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create monitor");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-200">Create Monitor</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-lg">&times;</button>
        </div>

        <div className="px-6 py-5">
          {step === 0 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Monitor Name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Austin Housing Prices"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Monitor Type</label>
                <div className="grid grid-cols-2 gap-2">
                  {MONITOR_TYPES.map((t) => (
                    <button
                      key={t.value}
                      onClick={() => setMonitorType(t.value)}
                      className={`text-left px-3 py-2.5 rounded-lg border text-sm transition-colors ${
                        monitorType === t.value
                          ? "border-indigo-500 bg-indigo-500/10 text-indigo-400"
                          : "border-gray-700 hover:border-gray-600 text-gray-400"
                      }`}
                    >
                      <div className="font-medium">{t.label}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{t.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
              <button
                onClick={() => setStep(1)}
                disabled={!name || !monitorType}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
              >
                Next: Configure
              </button>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">URL to Monitor</label>
                <input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/page-to-track"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Check Schedule</label>
                <div className="grid grid-cols-2 gap-2">
                  {SCHEDULES.map((s) => (
                    <button
                      key={s.value}
                      onClick={() => setSchedule(s.value)}
                      className={`px-3 py-2 rounded-lg border text-sm ${
                        schedule === s.value
                          ? "border-indigo-500 bg-indigo-500/10 text-indigo-400"
                          : "border-gray-700 text-gray-400 hover:border-gray-600"
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setStep(0)}
                  className="flex-1 py-2 border border-gray-700 rounded-lg text-sm text-gray-400 hover:bg-gray-800"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(2)}
                  className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium"
                >
                  Next: Alerts
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Email for Alerts (optional)</label>
                <input
                  value={alertEmail}
                  onChange={(e) => setAlertEmail(e.target.value)}
                  placeholder="you@example.com"
                  type="email"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Dashboard alerts are always enabled. Add email for notifications.
                </p>
              </div>
              {error && <p className="text-sm text-red-400">{error}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-2 border border-gray-700 rounded-lg text-sm text-gray-400 hover:bg-gray-800"
                >
                  Back
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-sm font-medium"
                >
                  {submitting ? "Creating..." : "Create Monitor"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
