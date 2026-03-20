"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { useAuth } from "@/components/AuthProvider";
import Nav from "@/components/Nav";

export default function AuthGate({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const isLoginPage = pathname === "/login";

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated && !isLoginPage) {
      router.replace("/login");
    }

    if (isAuthenticated && isLoginPage) {
      router.replace("/");
    }
  }, [isAuthenticated, isLoading, isLoginPage, router]);

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="inline-block w-6 h-6 border-2 border-gray-700 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading...</p>
        </div>
      </div>
    );
  }

  // Login page: render without nav
  if (isLoginPage) {
    return <>{children}</>;
  }

  // Not authenticated and not on login: will redirect (show nothing)
  if (!isAuthenticated) {
    return null;
  }

  // Authenticated: render normal layout with nav
  return (
    <div className="flex min-h-screen">
      <Nav />
      <main className="flex-1 ml-64 p-8 overflow-auto">{children}</main>
    </div>
  );
}
