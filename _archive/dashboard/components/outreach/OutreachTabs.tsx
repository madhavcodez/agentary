"use client";

import { cn } from "@/lib/cn";
import type { Tab } from "@/lib/hooks/useOutreachData";

const TABS: { key: Tab; label: string; desc: string; icon: string }[] = [
  {
    key: "networking",
    label: "Networking",
    desc: "Contacts grouped by company",
    icon: "M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z",
  },
  {
    key: "outreach",
    label: "Cold Outreach",
    desc: "Multi-channel campaigns",
    icon: "M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5",
  },
  {
    key: "conversations",
    label: "Conversations",
    desc: "Active campaign timelines",
    icon: "M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155",
  },
  {
    key: "ideas",
    label: "Ideas",
    desc: "AI research & autopilot",
    icon: "M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18",
  },
];

interface OutreachTabsProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

export default function OutreachTabs({
  activeTab,
  onTabChange,
}: OutreachTabsProps) {
  return (
    <div className="grid grid-cols-4 gap-3 mb-6">
      {TABS.map((t) => (
        <button
          key={t.key}
          onClick={() => onTabChange(t.key)}
          className={cn(
            "p-3 rounded-xl text-left transition-all duration-150 border flex items-start gap-3",
            activeTab === t.key
              ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400"
              : "bg-gray-900 border-gray-800 text-gray-400 hover:border-gray-700 hover:text-gray-300",
          )}
        >
          <svg
            className={cn(
              "w-5 h-5 mt-0.5 shrink-0",
              activeTab === t.key ? "text-indigo-400" : "text-gray-600",
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d={t.icon}
            />
          </svg>
          <div>
            <div className="text-sm font-semibold">{t.label}</div>
            <div className="text-[10px] mt-0.5 opacity-70">{t.desc}</div>
          </div>
        </button>
      ))}
    </div>
  );
}
