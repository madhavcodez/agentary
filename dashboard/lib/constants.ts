// ── Shared Constants ────────────────────────────────────────────────
// Extracted from individual pages to avoid duplication.

// ── Status badge colors (mission page + dashboard ActiveMissions) ────
export const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-500",
  queued: "bg-yellow-500",
  active: "bg-emerald-500",
  running: "bg-blue-500 animate-pulse",
  paused: "bg-orange-500",
  pending: "bg-amber-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

// ── Activity type icons (mission page + dashboard LiveActivityFeed) ──
export const ACTIVITY_ICONS: Record<string, string> = {
  thinking: "\u{1F914}",
  searching: "\u{1F50D}",
  scraping: "\u{1F310}",
  calling: "\u{1F4DE}",
  analyzing: "\u{1F4CA}",
  writing: "\u270D\uFE0F",
  found_data: "\u{1F4CB}",
  found_insight: "\u{1F4A1}",
  error: "\u26A0\uFE0F",
  delegating: "\u{1F4E4}",
  synthesizing: "\u{1F9E0}",
};

// ── Project type icons (home page + project page + projects list) ────
export const TYPE_ICONS: Record<string, string> = {
  real_estate: "\u{1F3E0}",
  competitive_intel: "\u{1F50D}",
  due_diligence: "\u{1F4CB}",
  data_extraction: "\u{1F4CA}",
  market_research: "\u{1F4C8}",
  local_business: "\u{1F3EA}",
  custom: "\u2699\uFE0F",
};

// ── Project type badge colors (projects list) ────────────────────────
export const TYPE_COLORS: Record<string, string> = {
  real_estate: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  competitive_intel: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  due_diligence: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  data_extraction: "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  market_research: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  local_business: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  custom: "text-gray-400 bg-gray-400/10 border-gray-400/20",
};
