import { cn } from "@/lib/cn";

interface ConfidenceBadgeProps {
  confidence: number | null;
  className?: string;
}

type ConfidenceLevel = "high" | "medium" | "low" | "na";

function getConfidenceLevel(confidence: number | null): ConfidenceLevel {
  if (confidence === null || confidence === undefined) return "na";
  if (confidence >= 0.8) return "high";
  if (confidence >= 0.5) return "medium";
  return "low";
}

const LEVEL_CONFIG: Record<
  ConfidenceLevel,
  { bgClass: string; textClass: string; borderClass: string; label: string }
> = {
  high: {
    bgClass: "bg-emerald-500/10",
    textClass: "text-emerald-400",
    borderClass: "border-emerald-500/20",
    label: "High",
  },
  medium: {
    bgClass: "bg-amber-500/10",
    textClass: "text-amber-400",
    borderClass: "border-amber-500/20",
    label: "Medium",
  },
  low: {
    bgClass: "bg-red-500/10",
    textClass: "text-red-400",
    borderClass: "border-red-500/20",
    label: "Low",
  },
  na: {
    bgClass: "bg-gray-500/10",
    textClass: "text-gray-400",
    borderClass: "border-gray-500/20",
    label: "N/A",
  },
};

export default function ConfidenceBadge({
  confidence,
  className,
}: ConfidenceBadgeProps) {
  const level = getConfidenceLevel(confidence);
  const config = LEVEL_CONFIG[level];
  const pct = confidence !== null ? Math.round(confidence * 100) : null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-medium",
        config.bgClass,
        config.textClass,
        config.borderClass,
        className,
      )}
    >
      {config.label}
      {pct !== null && (
        <span className="opacity-70">{pct}%</span>
      )}
    </span>
  );
}
