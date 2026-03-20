import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "bg-gray-900 border border-gray-800 rounded-xl p-12 text-center",
        className,
      )}
    >
      {icon && <div className="flex justify-center mb-4">{icon}</div>}
      <p className="text-sm text-gray-400">{title}</p>
      {description && (
        <p className="text-xs text-gray-600 mt-1">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
