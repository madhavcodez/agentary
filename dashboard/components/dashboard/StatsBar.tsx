"use client";

interface StatsBarProps {
  activeMissions: number;
  totalFindings: number;
  activeMonitors: number;
  unreadAlerts: number;
  connectedClients: number;
}

export default function StatsBar({
  activeMissions,
  totalFindings,
  activeMonitors,
  unreadAlerts,
  connectedClients,
}: StatsBarProps) {
  const stats = [
    { label: "Active Missions", value: activeMissions, color: "text-indigo-400" },
    { label: "Findings Today", value: totalFindings, color: "text-emerald-400" },
    { label: "Monitors", value: activeMonitors, color: "text-cyan-400" },
    { label: "Alerts", value: unreadAlerts, color: unreadAlerts > 0 ? "text-red-400" : "text-gray-400" },
    { label: "Connected", value: connectedClients, color: "text-amber-400" },
  ];

  return (
    <div className="grid grid-cols-5 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-center"
        >
          <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
          <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
