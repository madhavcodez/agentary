import { cn } from "@/lib/cn";

interface Tab {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export default function Tabs({
  tabs,
  activeTab,
  onChange,
  className,
}: TabsProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-1 border-b border-gray-800",
        className,
      )}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              "relative px-4 py-2.5 text-sm font-medium transition-colors duration-150",
              "focus:outline-none",
              isActive
                ? "text-indigo-400"
                : "text-gray-500 hover:text-gray-300",
            )}
          >
            {tab.label}
            {isActive && (
              <span className="absolute inset-x-0 -bottom-px h-0.5 bg-indigo-500 rounded-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}
