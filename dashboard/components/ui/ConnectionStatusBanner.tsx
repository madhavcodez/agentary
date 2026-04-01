"use client";

import { useHealthCheck } from "@/lib/hooks/useHealthCheck";
import { useOnlineStatus } from "@/lib/hooks/useOnlineStatus";

/**
 * Shows a subtle warning banner when the backend is unreachable but
 * the browser is online (distinguishes from OfflineBanner).
 */
export default function ConnectionStatusBanner() {
  const online = useOnlineStatus();
  const { healthy } = useHealthCheck({ enabled: online });

  // Don't show if browser is offline (OfflineBanner handles that)
  // Only show if browser is online but backend is down
  if (!online || healthy) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[190] bg-rose-500/90 text-white text-center text-sm font-medium py-2 px-4 animate-slide-up">
      Backend unavailable &mdash; reconnecting automatically
    </div>
  );
}
