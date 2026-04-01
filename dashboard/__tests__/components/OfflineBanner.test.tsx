/**
 * Tests for the OfflineBanner component and useOnlineStatus hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import OfflineBanner from "@/components/ui/OfflineBanner";

describe("OfflineBanner", () => {
  let originalOnLine: boolean;

  beforeEach(() => {
    originalOnLine = navigator.onLine;
  });

  afterEach(() => {
    // Restore original state
    Object.defineProperty(navigator, "onLine", { value: originalOnLine, configurable: true });
  });

  it("does not render when online", () => {
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
    render(<OfflineBanner />);
    expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();
  });

  it("renders banner when offline", () => {
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
    render(<OfflineBanner />);
    expect(screen.getByText(/offline/i)).toBeInTheDocument();
    expect(screen.getByText(/changes will sync/i)).toBeInTheDocument();
  });

  it("shows banner when going offline and hides when back online", () => {
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
    render(<OfflineBanner />);

    expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();

    // Go offline
    act(() => {
      Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
      window.dispatchEvent(new Event("offline"));
    });

    expect(screen.getByText(/offline/i)).toBeInTheDocument();

    // Come back online
    act(() => {
      Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
      window.dispatchEvent(new Event("online"));
    });

    expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();
  });
});
