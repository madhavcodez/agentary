import { cn } from "@/lib/cn";
import { STATUS_COLORS } from "@/lib/constants";

interface StatusDotProps {
  status: string;
  /** Show the status label text next to the dot. */
  showLabel?: boolean;
  className?: string;
}

/** Small colored dot indicating entity status (mission, project, etc). */
export default function StatusDot({ status, showLabel = false, className }: StatusDotProps) {
  const dotColor = STATUS_COLORS[status] ?? "bg-gray-500";

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs text-gray-400", className)}>
      <span className={cn("w-2 h-2 rounded-full flex-shrink-0", dotColor)} />
      {showLabel && status}
    </span>
  );
}
