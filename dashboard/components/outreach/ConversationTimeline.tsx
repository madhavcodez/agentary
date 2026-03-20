"use client";

interface TimelineEvent {
  type: string;
  label: string;
  time: string;
  color: string;
}

interface ConversationTimelineProps {
  events: TimelineEvent[];
}

export default function ConversationTimeline({
  events,
}: ConversationTimelineProps) {
  if (events.length === 0) return null;

  const DOT_COLORS: Record<string, string> = {
    blue: "bg-blue-400",
    emerald: "bg-emerald-400",
    purple: "bg-purple-400",
  };

  return (
    <div className="relative pl-6">
      <div className="absolute left-2 top-1 bottom-1 w-px bg-gray-800" />
      {events.map((ev, i) => {
        const dotColor = DOT_COLORS[ev.color] ?? "bg-gray-400";
        return (
          <div key={i} className="relative pb-4 last:pb-0">
            <div
              className={`absolute left-[-16px] top-1 w-2.5 h-2.5 rounded-full border-2 border-gray-950 ${dotColor}`}
            />
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500">
                {new Date(ev.time).toLocaleDateString()}
              </span>
              <span className="text-sm text-gray-300">{ev.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
