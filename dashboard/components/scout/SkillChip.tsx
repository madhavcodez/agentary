"use client";

import { cn } from "@/lib/cn";

interface SkillChipProps {
  name: string;
  active: boolean;
  onToggle: (name: string) => void;
  disabled?: boolean;
}

export default function SkillChip({ name, active, onToggle, disabled }: SkillChipProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onToggle(name)}
      className={cn(
        "px-2.5 py-1 rounded-md text-xs font-medium border transition-all duration-150",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        active
          ? "bg-indigo-500/15 text-indigo-400 border-indigo-500/30"
          : "bg-gray-800/60 text-gray-400 border-gray-700/50 hover:bg-gray-800 hover:text-gray-300",
      )}
    >
      {name}
    </button>
  );
}
