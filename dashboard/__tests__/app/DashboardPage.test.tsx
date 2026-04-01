import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

// ── Mocks ────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/dashboard",
}));

const mockToast = vi.fn();
vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

// WebSocket mock with configurable state
let wsConnectionState = "connected";

vi.mock("@/components/WebSocketProvider", () => ({
  useWS: () => ({
    connectionState: wsConnectionState,
    subscribe: vi.fn(() => vi.fn()),
  }),
}));

// ── Child component mocks (keep tests isolated) ─────────────────────

vi.mock("@/components/dashboard/ActiveMissions", () => ({
  __esModule: true,
  default: ({ missions }: { missions: Array<{ id: string; title: string }> }) => (
    <div data-testid="active-missions">
      {missions.map((m) => (
        <div key={m.id}>{m.title}</div>
      ))}
    </div>
  ),
}));

vi.mock("@/components/dashboard/LiveActivityFeed", () => ({
  __esModule: true,
  default: () => <div data-testid="live-activity-feed">Activity Feed</div>,
}));

vi.mock("@/components/dashboard/MonitorsPanel", () => ({
  __esModule: true,
  default: ({ monitors }: { monitors: Array<{ id: string; name: string }> }) => (
    <div data-testid="monitors-panel">
      {monitors.map((m) => (
        <div key={m.id}>{m.name}</div>
      ))}
    </div>
  ),
}));

// ── API mocks ────────────────────────────────────────────────────────

const mockFetchRecentEvents = vi.fn();
const mockFetchMonitors = vi.fn();
const mockFetchMissions = vi.fn();
const mockFetchFindings = vi.fn();
const mockFetchUnreadAlertCount = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchRecentEvents: (...args: unknown[]) => mockFetchRecentEvents(...args),
  fetchMonitors: (...args: unknown[]) => mockFetchMonitors(...args),
  fetchMissions: (...args: unknown[]) => mockFetchMissions(...args),
  fetchFindings: (...args: unknown[]) => mockFetchFindings(...args),
  fetchUnreadAlertCount: (...args: unknown[]) =>
    mockFetchUnreadAlertCount(...args),
}));

// ── Import page under test (after mocks) ─────────────────────────────

import DashboardPage from "@/app/dashboard/page";

// ── Helpers ──────────────────────────────────────────────────────────

function setupDefaultMocks() {
  mockFetchRecentEvents.mockResolvedValue([]);
  mockFetchMonitors.mockResolvedValue([
    {
      id: "m1",
      user_id: "u1",
      project_id: null,
      name: "Monitor Alpha",
      description: null,
      monitor_type: "price",
      status: "active",
      check_config: {},
      alert_config: {},
      schedule_cron: null,
      timezone: "UTC",
      last_check_at: null,
      last_change_at: null,
      total_checks: 0,
      total_alerts: 0,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ]);
  mockFetchMissions.mockResolvedValue([
    {
      id: "mis-1",
      name: "Research Mission",
      status: "running",
      project_id: "p1",
      created_at: "2026-01-01T00:00:00Z",
    },
  ]);
  mockFetchFindings.mockResolvedValue([
    { id: "f1" },
    { id: "f2" },
    { id: "f3" },
  ]);
  mockFetchUnreadAlertCount.mockResolvedValue({ unread: 5 });
}

// ── Tests ────────────────────────────────────────────────────────────

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    wsConnectionState = "connected";
    setupDefaultMocks();
  });

  // ── Loading state ──────────────────────────────────────────────────

  it("renders skeleton while loading", () => {
    // Make APIs hang to keep loading state
    mockFetchRecentEvents.mockReturnValue(new Promise(() => {}));
    mockFetchMonitors.mockReturnValue(new Promise(() => {}));
    mockFetchMissions.mockReturnValue(new Promise(() => {}));
    mockFetchFindings.mockReturnValue(new Promise(() => {}));
    mockFetchUnreadAlertCount.mockReturnValue(new Promise(() => {}));

    render(<DashboardPage />);

    const skeleton = document.querySelector(".animate-pulse");
    expect(skeleton).toBeInTheDocument();
  });

  // ── Heading ────────────────────────────────────────────────────────

  it('shows "System Dashboard" heading', async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("System Dashboard")).toBeInTheDocument();
    });
  });

  // ── Connection status dot ──────────────────────────────────────────

  it("shows green connection dot when connected", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("System Dashboard")).toBeInTheDocument();
    });

    const dot = document.querySelector(".bg-emerald-400");
    expect(dot).toBeInTheDocument();
  });

  it("shows amber pulsing dot when reconnecting", async () => {
    wsConnectionState = "reconnecting";

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("System Dashboard")).toBeInTheDocument();
    });

    const dot = document.querySelector(".bg-amber-400.animate-pulse");
    expect(dot).toBeInTheDocument();
  });

  // ── Active Missions panel ──────────────────────────────────────────

  it("renders Active Missions panel", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("active-missions")).toBeInTheDocument();
    });

    expect(screen.getByText("Research Mission")).toBeInTheDocument();
  });

  // ── Monitors panel ─────────────────────────────────────────────────

  it("renders Monitors panel", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("monitors-panel")).toBeInTheDocument();
    });

    expect(screen.getByText("Monitor Alpha")).toBeInTheDocument();
  });

  // ── Findings count and unread alerts badge ─────────────────────────

  it("shows findings count and unread alerts badge", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Active Findings")).toBeInTheDocument();
    });

    // Total findings count (3 findings returned from mock)
    expect(screen.getByText("3")).toBeInTheDocument();

    // Unread alerts badge
    expect(screen.getByText("5 unread alerts")).toBeInTheDocument();
  });

  it("does not show unread badge when count is 0", async () => {
    mockFetchUnreadAlertCount.mockResolvedValue({ unread: 0 });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Active Findings")).toBeInTheDocument();
    });

    expect(screen.queryByText(/unread alert/)).not.toBeInTheDocument();
  });

  // ── Connection states ──────────────────────────────────────────────

  it("shows red dot when disconnected", async () => {
    wsConnectionState = "disconnected";

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("System Dashboard")).toBeInTheDocument();
    });

    const dot = document.querySelector(".bg-red-400");
    expect(dot).toBeInTheDocument();
  });

  // ── API interaction ────────────────────────────────────────────────

  it("calls all API endpoints on mount", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("System Dashboard")).toBeInTheDocument();
    });

    expect(mockFetchRecentEvents).toHaveBeenCalledWith(20);
    expect(mockFetchMonitors).toHaveBeenCalled();
    expect(mockFetchMissions).toHaveBeenCalled();
    expect(mockFetchFindings).toHaveBeenCalledWith({ limit: 100 });
    expect(mockFetchUnreadAlertCount).toHaveBeenCalled();
  });

  // ── Partial failure ────────────────────────────────────────────────

  it("shows toast on partial API failure and still renders", async () => {
    mockFetchMonitors.mockRejectedValue(new Error("timeout"));

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("System Dashboard")).toBeInTheDocument();
    });

    expect(mockToast).toHaveBeenCalledWith(
      "Some dashboard data failed to load",
      "error",
    );
  });
});
