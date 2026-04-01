import { cn } from "@/lib/cn";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export default function Card({
  children,
  className,
  hover = false,
  onClick,
}: CardProps) {
  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") onClick(); } : undefined}
      className={cn(
        "bg-[#131820] border border-white/[0.06] rounded-xl p-6 transition-all duration-[180ms]",
        hover &&
          "card-hover cursor-pointer hover:border-white/[0.12] hover:bg-[#181e28]",
        onClick && "cursor-pointer focus-visible:ring-2 focus-visible:ring-emerald-500/40 focus-visible:outline-none",
        className,
      )}
    >
      {children}
    </div>
  );
}
