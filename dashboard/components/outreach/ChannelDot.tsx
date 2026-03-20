import { cn } from "@/lib/cn";

const CHANNEL_COLORS: Record<string, Record<string, string>> = {
  email: {
    sent: "bg-blue-400",
    draft: "bg-blue-400/40",
    none: "bg-gray-600",
    pending: "bg-gray-500",
    failed: "bg-red-400",
    completed: "bg-blue-400",
  },
  call: {
    completed: "bg-emerald-400",
    pending: "bg-gray-500",
    none: "bg-gray-600",
    sent: "bg-emerald-400",
    draft: "bg-emerald-400/40",
    failed: "bg-red-400",
  },
  linkedin: {
    sent: "bg-purple-400",
    draft: "bg-purple-400/40",
    none: "bg-gray-600",
    pending: "bg-gray-500",
    failed: "bg-red-400",
    completed: "bg-purple-400",
  },
};

const LABELS: Record<string, string> = {
  email: "Email",
  call: "Call",
  linkedin: "LinkedIn",
};

interface ChannelDotProps {
  status: string;
  channel: "email" | "call" | "linkedin";
}

export default function ChannelDot({ status, channel }: ChannelDotProps) {
  const bg = CHANNEL_COLORS[channel]?.[status] ?? "bg-gray-600";

  return (
    <div className="flex items-center gap-1.5">
      <div className={cn("w-2 h-2 rounded-full", bg)} />
      <span className="text-[10px] text-gray-500">{LABELS[channel]}</span>
    </div>
  );
}
