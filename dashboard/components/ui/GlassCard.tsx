import { cn } from "@/lib/cn";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  pulse?: boolean;
}

export default function GlassCard({
  children,
  className,
  hover = false,
  pulse = false,
}: GlassCardProps) {
  return (
    <div
      className={cn(
        "glass-card rounded-2xl",
        hover && "hover:shadow-[0_0_20px_4px_rgba(16,185,129,0.12)] transition-all duration-[180ms]",
        pulse && "pulse-glow",
        className,
      )}
    >
      {children}
    </div>
  );
}
