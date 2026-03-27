"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";
import Nav from "@/components/Nav";

export default function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (pathname === "/login") {
      router.replace("/");
    }
  }, [pathname, router]);

  if (pathname === "/login") {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-gray-950">
      <Nav />
      <main className="flex-1 ml-64 p-8 overflow-auto">{children}</main>
    </div>
  );
}
