"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import dynamic from "next/dynamic";
import Nav from "@/components/Nav";

// Lazy-load banners client-side only to avoid hydration mismatch
// (they use browser APIs: navigator.onLine, fetch)
const OfflineBanner = dynamic(() => import("@/components/ui/OfflineBanner"), { ssr: false });
const ConnectionStatusBanner = dynamic(() => import("@/components/ui/ConnectionStatusBanner"), { ssr: false });

export default function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (pathname === "/login") {
      router.replace("/");
    }
  }, [pathname, router]);

  // Always render the same structure for SSR — hide content via CSS if on login
  // This prevents hydration mismatch from conditional returns
  return (
    <div className={`flex min-h-screen bg-[#0d1017] ${pathname === "/login" ? "hidden" : ""}`}>
      {mounted && <OfflineBanner />}
      {mounted && <ConnectionStatusBanner />}
      <Nav />
      <main className="flex-1 ml-56 p-8 overflow-auto">{children}</main>
    </div>
  );
}
