interface ScoreBadgeProps {
  score: number;
  label?: string;
  size?: "sm" | "md" | "lg";
}

export default function ScoreBadge({ score, label, size = "md" }: ScoreBadgeProps) {
  const rounded = Math.round(score);

  const colorClasses =
    rounded >= 70
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      : rounded >= 40
        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
        : "bg-red-500/10 text-red-400 border-red-500/20";

  const sizeClasses =
    size === "lg"
      ? "px-3 py-1.5 text-base"
      : size === "sm"
        ? "px-1.5 py-0.5 text-xs"
        : "px-2 py-1 text-sm";

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-md border font-semibold
        ${colorClasses} ${sizeClasses}
      `}
    >
      {label && <span className="font-normal opacity-70">{label}</span>}
      {rounded}
    </span>
  );
}
