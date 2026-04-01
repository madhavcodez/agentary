"use client";

import { cn } from "@/lib/cn";

interface SkeletonProps {
  className?: string;
}

/** Pulsing placeholder for content that is loading. */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg bg-white/[0.06]",
        className,
      )}
    />
  );
}

/** Card-shaped skeleton matching GlassCard dimensions. */
export function SkeletonCard({ className }: SkeletonProps) {
  return (
    <div className={cn("glass-card rounded-2xl p-6 space-y-3", className)}>
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-3 w-2/3" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  );
}

/** Row skeleton for list items. */
export function SkeletonRow({ className }: SkeletonProps) {
  return (
    <div className={cn("flex items-center gap-3 py-3", className)}>
      <Skeleton className="w-2 h-2 rounded-full" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3.5 w-3/5" />
        <Skeleton className="h-2.5 w-2/5" />
      </div>
    </div>
  );
}

/** Full dashboard skeleton layout. */
export function DashboardSkeleton() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-6 space-y-5">
      <Skeleton className="h-6 w-48" />
      <SkeletonCard className="max-h-[220px]" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <Skeleton className="h-10 w-full rounded-xl" />
    </div>
  );
}

/** Mission page skeleton layout. */
export function MissionSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-8 py-8 space-y-6">
      <SkeletonCard className="h-40" />
      <div className="flex gap-3">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-14 w-32 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-8 w-64" />
      <SkeletonCard className="h-96" />
    </div>
  );
}

/** Project page skeleton layout. */
export function ProjectSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-8 py-8 space-y-6">
      <Skeleton className="h-4 w-32" />
      <div className="flex items-center gap-3">
        <Skeleton className="h-8 w-8 rounded-lg" />
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <SkeletonCard className="h-80" />
      <Skeleton className="h-14 w-full rounded-2xl" />
    </div>
  );
}
