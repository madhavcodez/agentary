"use client";

interface StatsBarProps {
  activeMissions: number;
  totalFindings: number;
  activeMonitors: number;
  unreadAlerts: number;
}

export default function StatsBar({
  activeMissions,
  totalFindings,
  activeMonitors,
  unreadAlerts,
}: StatsBarProps) {
  const stats = [
    { label: "Active Missions", value: activeMissions, color: "text-emerald-400" },
    { label: "Findings", value: totalFindings, color: "text-gray-100" },
    { label: "Monitors", value: activeMonitors, color: "text-gray-100" },
    { label: "Alerts", value: unreadAlerts, color: unreadAlerts > 0 ? "text-red-400" : "text-gray-400" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-[#131820] border border-white/[0.06] rounded-xl px-5 py-4 text-center transition-all duration-[180ms] hover:border-white/[0.12]"
        >
          <div className={`text-2xl font-bold tabular-nums ${stat.color}`}>{stat.value}</div>
          <div className="text-[11px] text-gray-500 mt-1.5 uppercase tracking-wider font-medium">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
