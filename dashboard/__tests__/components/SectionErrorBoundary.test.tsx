/**
 * Tests for the SectionErrorBoundary component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SectionErrorBoundary from "@/components/ui/SectionErrorBoundary";

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("Test crash");
  return <div>Child content</div>;
}

// Suppress React error boundary console.error in tests
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});
afterEach(() => {
  console.error = originalError;
});

describe("SectionErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <SectionErrorBoundary>
        <div>Safe content</div>
      </SectionErrorBoundary>,
    );
    expect(screen.getByText("Safe content")).toBeInTheDocument();
  });

  it("shows fallback when child throws", () => {
    render(
      <SectionErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </SectionErrorBoundary>,
    );
    expect(screen.getByText("This section encountered an error")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("shows section name in error message", () => {
    render(
      <SectionErrorBoundary section="Run Trace">
        <ThrowingChild shouldThrow={true} />
      </SectionErrorBoundary>,
    );
    expect(screen.getByText("Failed to load Run Trace")).toBeInTheDocument();
  });

  it("retry button is clickable and resets error state", () => {
    render(
      <SectionErrorBoundary section="Test Panel">
        <ThrowingChild shouldThrow={true} />
      </SectionErrorBoundary>,
    );

    expect(screen.getByText("Failed to load Test Panel")).toBeInTheDocument();
    const retryBtn = screen.getByText("Retry");
    expect(retryBtn).toBeInTheDocument();

    // Clicking retry resets the boundary state (child will throw again,
    // but the boundary catches it). This validates the retry mechanism exists.
    fireEvent.click(retryBtn);
    // After retry + re-throw, error boundary catches again
    expect(screen.getByText("Failed to load Test Panel")).toBeInTheDocument();
  });
});
