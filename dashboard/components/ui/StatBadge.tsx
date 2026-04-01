import { cn } from "@/lib/cn";

interface StatBadgeProps {
  value: number | string;
  label: string;
  className?: string;
}

/** Compact stat badge used for inline metrics (e.g., "5 missions"). */
export default function StatBadge({ value, label, className }: StatBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full glass-card text-gray-300",
        className,
      )}
    >
      <span className="font-semibold text-gray-100">{value}</span>
      {label}
    </span>
  );
}
