import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import GlassCard from "@/components/ui/GlassCard";
import StatBadge from "@/components/ui/StatBadge";
import StatusDot from "@/components/ui/StatusDot";

describe("GlassCard", () => {
  it("renders children with glass-card class", () => {
    const { container } = render(<GlassCard>Card content</GlassCard>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
    const el = container.firstChild as HTMLElement;
    expect(el.classList.contains("glass-card")).toBe(true);
  });

  it("applies custom className", () => {
    const { container } = render(<GlassCard className="rounded-xl p-4">Test</GlassCard>);
    const el = container.firstChild as HTMLElement;
    expect(el.classList.contains("rounded-xl")).toBe(true);
    expect(el.classList.contains("p-4")).toBe(true);
  });

  it("applies hover glow when hover prop is true", () => {
    const { container } = render(<GlassCard hover>Hoverable</GlassCard>);
    const el = container.firstChild as HTMLElement;
    // Should have the hover shadow class in its className
    expect(el.className).toContain("hover:");
  });

  it("applies pulse-glow when pulse prop is true", () => {
    const { container } = render(<GlassCard pulse>Pulsing</GlassCard>);
    const el = container.firstChild as HTMLElement;
    expect(el.classList.contains("pulse-glow")).toBe(true);
  });
});

describe("StatBadge", () => {
  it("renders value and label", () => {
    render(<StatBadge value={42} label="missions" />);
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("missions")).toBeInTheDocument();
  });

  it("renders string values", () => {
    render(<StatBadge value="N/A" label="status" />);
    expect(screen.getByText("N/A")).toBeInTheDocument();
  });
});

describe("StatusDot", () => {
  it("renders a dot without label by default", () => {
    const { container } = render(<StatusDot status="running" />);
    const dot = container.querySelector(".rounded-full");
    expect(dot).toBeTruthy();
    expect(screen.queryByText("running")).not.toBeInTheDocument();
  });

  it("shows label when showLabel is true", () => {
    render(<StatusDot status="completed" showLabel />);
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("uses correct color for known statuses", () => {
    const { container } = render(<StatusDot status="failed" />);
    const dot = container.querySelector(".rounded-full");
    expect(dot?.classList.contains("bg-red-500")).toBe(true);
  });

  it("uses gray for unknown statuses", () => {
    const { container } = render(<StatusDot status="unknown_state" />);
    const dot = container.querySelector(".rounded-full");
    expect(dot?.classList.contains("bg-gray-500")).toBe(true);
  });
});
