"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function DashboardMonitorsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/monitors");
  }, [router]);
  return null;
}
