import { cn } from "@/lib/cn";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export default function Card({
  children,
  className,
  hover = false,
}: CardProps) {
  return (
    <div
      className={cn(
        "bg-gray-900 border border-gray-800 rounded-xl p-6",
        hover &&
          "hover:border-gray-700 hover:bg-gray-900/80 transition-all duration-200",
        className,
      )}
    >
      {children}
    </div>
  );
}
