"use client";

import { useOnlineStatus } from "@/lib/hooks/useOnlineStatus";

/**
 * Fixed banner shown at the top of the viewport when the browser goes offline.
 * Automatically hides when connectivity is restored.
 */
export default function OfflineBanner() {
  const online = useOnlineStatus();

  if (online) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[200] bg-amber-500/90 text-amber-950 text-center text-sm font-medium py-2 px-4 animate-slide-up">
      You&apos;re offline &mdash; changes will sync when reconnected
    </div>
  );
}
