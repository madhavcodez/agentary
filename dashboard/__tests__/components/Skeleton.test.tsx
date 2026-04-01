import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import {
  Skeleton,
  SkeletonCard,
  SkeletonRow,
  DashboardSkeleton,
  MissionSkeleton,
  ProjectSkeleton,
} from "@/components/ui/Skeleton";

describe("Skeleton components", () => {
  it("Skeleton renders with animate-pulse class", () => {
    const { container } = render(<Skeleton className="h-4 w-32" />);
    const el = container.firstChild as HTMLElement;
    expect(el.classList.contains("animate-pulse")).toBe(true);
    expect(el.classList.contains("rounded-lg")).toBe(true);
  });

  it("SkeletonCard renders a card with 3 skeleton rows", () => {
    const { container } = render(<SkeletonCard />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThanOrEqual(3);
  });

  it("SkeletonRow renders a dot and two lines", () => {
    const { container } = render(<SkeletonRow />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    // dot + 2 text lines = 3
    expect(skeletons.length).toBe(3);
  });

  it("DashboardSkeleton renders the full layout shape", () => {
    const { container } = render(<DashboardSkeleton />);
    // Should have multiple skeleton elements for the dashboard layout
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThanOrEqual(5);
  });

  it("MissionSkeleton renders the mission page shape", () => {
    const { container } = render(<MissionSkeleton />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThanOrEqual(5);
  });

  it("ProjectSkeleton renders the project page shape", () => {
    const { container } = render(<ProjectSkeleton />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThanOrEqual(4);
  });

  it("Skeleton accepts custom className", () => {
    const { container } = render(<Skeleton className="h-10 w-full" />);
    const el = container.firstChild as HTMLElement;
    expect(el.classList.contains("h-10")).toBe(true);
    expect(el.classList.contains("w-full")).toBe(true);
  });
});
