"use client";

import { cn } from "@/lib/cn";

interface FreshnessIndicatorProps {
  freshnessAt: string;
  thresholdHours?: number;
  className?: string;
}

function getAgeHours(freshnessAt: string): number {
  const now = Date.now();
  const then = new Date(freshnessAt).getTime();
  return (now - then) / (1000 * 60 * 60);
}

function formatTimeAgo(freshnessAt: string): string {
  const ageHours = getAgeHours(freshnessAt);
  if (ageHours < 1) {
    const minutes = Math.round(ageHours * 60);
    return `${minutes}m ago`;
  }
  if (ageHours < 24) {
    return `${Math.round(ageHours)}h ago`;
  }
  const days = Math.round(ageHours / 24);
  return `${days}d ago`;
}

type FreshnessLevel = "fresh" | "aging" | "stale";

function getFreshnessLevel(
  freshnessAt: string,
  thresholdHours: number,
): FreshnessLevel {
  const ageHours = getAgeHours(freshnessAt);
  const halfThreshold = thresholdHours * 0.5;

  if (ageHours <= halfThreshold) return "fresh";
  if (ageHours <= thresholdHours) return "aging";
  return "stale";
}

const LEVEL_CONFIG: Record<
  FreshnessLevel,
  { dotClass: string; label: string; textClass: string }
> = {
  fresh: {
    dotClass: "bg-emerald-400",
    label: "Fresh",
    textClass: "text-emerald-400",
  },
  aging: {
    dotClass: "bg-amber-400",
    label: "Aging",
    textClass: "text-amber-400",
  },
  stale: {
    dotClass: "bg-red-400",
    label: "Stale",
    textClass: "text-red-400",
  },
};

export default function FreshnessIndicator({
  freshnessAt,
  thresholdHours = 168,
  className,
}: FreshnessIndicatorProps) {
  const level = getFreshnessLevel(freshnessAt, thresholdHours);
  const config = LEVEL_CONFIG[level];
  const timeAgo = formatTimeAgo(freshnessAt);

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <span
        className={cn("w-1.5 h-1.5 rounded-full shrink-0", config.dotClass)}
      />
      <span className={cn("text-xs font-medium", config.textClass)}>
        {config.label}
      </span>
      <span className="text-xs text-gray-500">
        {timeAgo}
      </span>
    </div>
  );
}
