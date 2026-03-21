"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { acknowledgeAlert, fetchAlerts, fetchUnreadAlertCount } from "@/lib/api";
import type { AlertItem } from "@/lib/types";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "border-l-red-500 bg-red-500/5",
  warning: "border-l-amber-500 bg-amber-500/5",
  info: "border-l-blue-500 bg-blue-500/5",
};

export default function AlertCenter() {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [unread, setUnread] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const loadAlerts = useCallback(async () => {
    try {
      const [items, count] = await Promise.all([
        fetchAlerts({ limit: 20 }),
        fetchUnreadAlertCount(),
      ]);
      setAlerts(items);
      setUnread(count.unread);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(loadAlerts, 30000);
    return () => clearInterval(interval);
  }, [loadAlerts]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const handleAck = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId);
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a)),
      );
      setUnread((prev) => Math.max(0, prev - 1));
    } catch {
      // silently fail
    }
  };

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-gray-800 transition-colors"
        aria-label="Alerts"
      >
        <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-96 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 max-h-96 overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-200">Alerts</h3>
            {unread > 0 && (
              <span className="text-xs text-red-400">{unread} unread</span>
            )}
          </div>
          <div className="overflow-y-auto flex-1">
            {alerts.length === 0 && (
              <div className="px-4 py-8 text-center text-sm text-gray-500">
                No alerts
              </div>
            )}
            {alerts.map((a) => (
              <div
                key={a.id}
                className={`px-4 py-3 border-l-2 border-b border-gray-800 ${
                  SEVERITY_COLORS[a.severity] ?? ""
                } ${a.acknowledged ? "opacity-60" : ""}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-gray-200 leading-snug">{a.title}</div>
                    {a.message && (
                      <div className="text-xs text-gray-500 mt-0.5">{a.message}</div>
                    )}
                    <div className="text-xs text-gray-600 mt-1">
                      {a.created_at
                        ? new Date(a.created_at).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : ""}
                    </div>
                  </div>
                  {!a.acknowledged && (
                    <button
                      onClick={() => handleAck(a.id)}
                      className="text-xs text-gray-500 hover:text-emerald-400 shrink-0 mt-0.5"
                      title="Acknowledge"
                    >
                      Ack
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
