"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useWS } from "@/components/WebSocketProvider";
import { fetchPendingActions } from "@/lib/api";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ active: boolean }>;
  badge?: boolean;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Overview",
    items: [
      { href: "/", label: "Home", icon: HomeIcon },
      { href: "/dashboard", label: "Dashboard", icon: DashboardIcon },
      { href: "/projects", label: "Projects", icon: ProjectsIcon },
    ],
  },
  {
    title: "Execution",
    items: [
      { href: "/missions", label: "Missions", icon: MissionsIcon },
      { href: "/workflows", label: "Workflows", icon: WorkflowsIcon },
      { href: "/voice", label: "Voice", icon: VoiceIcon },
      { href: "/reports", label: "Reports", icon: ReportsIcon },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { href: "/signals", label: "Signals", icon: SignalsIcon },
      { href: "/recommendations", label: "Recommendations", icon: RecommendationsIcon },
      { href: "/approvals", label: "Approvals", icon: ApprovalsIcon, badge: true },
      { href: "/actions", label: "Actions", icon: ActionsIcon },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/monitors", label: "Monitors", icon: MonitorsIcon },
      { href: "/analytics", label: "Analytics", icon: AnalyticsIcon },
      { href: "/operator", label: "Operator", icon: OperatorIcon },
      { href: "/settings", label: "Settings", icon: SettingsIcon },
    ],
  },
];

const CONNECTION_DOT: Record<string, { color: string; label: string }> = {
  connected: { color: "bg-emerald-400", label: "Connected" },
  connecting: { color: "bg-yellow-400 animate-pulse", label: "Connecting..." },
  reconnecting: { color: "bg-yellow-400 animate-pulse", label: "Reconnecting..." },
  disconnected: { color: "bg-red-400", label: "Disconnected" },
};

export default function Nav() {
  const pathname = usePathname();
  const { connectionState } = useWS();
  const dot = CONNECTION_DOT[connectionState] ?? CONNECTION_DOT.disconnected;
  const [pendingCount, setPendingCount] = useState(0);

  const loadPendingCount = useCallback(async () => {
    try {
      const data = await fetchPendingActions();
      setPendingCount(data.length);
    } catch {
      // Silently fail - badge is non-critical
    }
  }, []);

  useEffect(() => {
    // Delay initial fetch to not block page load
    const initialTimeout = setTimeout(loadPendingCount, 3000);
    // Poll every 60s (not 30s) to reduce load
    const interval = setInterval(loadPendingCount, 60000);
    return () => {
      clearTimeout(initialTimeout);
      clearInterval(interval);
    };
  }, [loadPendingCount]);

  function isActive(href: string): boolean {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-gray-950 border-r border-gray-800/50 flex flex-col z-50">
      <Link href="/" className="block px-6 py-5 border-b border-gray-800/50">
        <h1 className="text-lg font-semibold tracking-tight">
          <span className="text-emerald-400">Agent</span>
          <span className="text-gray-100">ary</span>
        </h1>
        <p className="text-[11px] text-gray-600 mt-0.5">Research & Intelligence</p>
      </Link>

      <nav className="flex-1 px-3 py-3 overflow-y-auto" aria-label="Main navigation">
        {NAV_SECTIONS.map((section, idx) => (
          <div key={section.title} className={idx > 0 ? "mt-5" : ""}>
            <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-600">
              {section.title}
            </p>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = isActive(item.href);
                const showBadge = item.badge && pendingCount > 0;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 ${
                      active
                        ? "bg-gray-800/80 text-gray-100"
                        : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/40"
                    }`}
                  >
                    <item.icon active={active} />
                    <span className="flex-1">{item.label}</span>
                    {showBadge && (
                      <span className="min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-amber-500 text-[10px] font-bold text-gray-950 px-1" aria-label={`${pendingCount} pending approvals`}>
                        {pendingCount > 99 ? "99+" : pendingCount}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-gray-800/50">
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${dot.color}`} />
          <span className="text-[11px] text-gray-600">{dot.label}</span>
        </div>
      </div>
    </aside>
  );
}

function HomeIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
    </svg>
  );
}

function DashboardIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
    </svg>
  );
}

function ProjectsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
    </svg>
  );
}

function MissionsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
    </svg>
  );
}

function WorkflowsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  );
}

function VoiceIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
    </svg>
  );
}

function ReportsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    </svg>
  );
}

function MonitorsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
    </svg>
  );
}

function AnalyticsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  );
}

function SettingsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function SignalsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.348 14.651a3.75 3.75 0 010-5.303m5.304 0a3.75 3.75 0 010 5.303m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.789m13.788 0c3.808 3.808 3.808 9.981 0 13.79M12 12h.008v.007H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
    </svg>
  );
}

function RecommendationsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
    </svg>
  );
}

function ApprovalsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0M3.124 7.5A8.969 8.969 0 015.292 3m13.416 0a8.969 8.969 0 012.168 4.5" />
    </svg>
  );
}

function ActionsIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
    </svg>
  );
}

function OperatorIcon({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? "text-gray-100" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
    </svg>
  );
}
