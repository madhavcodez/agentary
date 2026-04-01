import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, type Mock } from "vitest";

// ── Mocks ────────────────────────────────────────────────────────────

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useParams: () => ({ missionId: "test-mission-id" }),
  usePathname: () => "/missions/test-mission-id",
}));

vi.mock("@/components/WebSocketProvider", () => ({
  useWS: () => ({
    connectionState: "connected",
    subscribe: vi.fn(() => vi.fn()),
  }),
}));

vi.mock("@/components/ui/FindingModal", () => ({
  __esModule: true,
  default: ({
    finding,
    onClose,
  }: {
    finding: { title: string };
    onClose: () => void;
  }) => (
    <div data-testid="finding-modal">
      <span>{finding.title}</span>
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

// ── API mock factory ─────────────────────────────────────────────────

function makeMissionStatus(overrides: Record<string, unknown> = {}) {
  return {
    mission_id: "test-mission-id",
    latest_run_id: null,
    status: "completed",
    findings_count: 3,
    confidence_score: 0.85,
    crew: { agents: [] },
    activities: [],
    ...overrides,
  };
}

function makeFinding(overrides: Record<string, unknown> = {}) {
  return {
    id: "f1",
    category: "market",
    title: "Finding 1",
    content: "Content of finding 1",
    confidence: 0.9,
    tags: ["tag-a"],
    verified: false,
    source_type: null,
    source_url: null,
    source_name: null,
    structured_data: null,
    created_at: null,
    ...overrides,
  };
}

const mockFetchMissionStatus = vi.fn();
const mockFetchMissionFindings = vi.fn();
const mockFetchRunSteps = vi.fn();
const mockStartMission = vi.fn();
const mockStopMission = vi.fn();
const mockRerunMission = vi.fn();
const mockSynthesizeMissionReport = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchMissionStatus: (...args: unknown[]) => mockFetchMissionStatus(...args),
  fetchMissionFindings: (...args: unknown[]) =>
    mockFetchMissionFindings(...args),
  fetchRunSteps: (...args: unknown[]) => mockFetchRunSteps(...args),
  startMission: (...args: unknown[]) => mockStartMission(...args),
  stopMission: (...args: unknown[]) => mockStopMission(...args),
  rerunMission: (...args: unknown[]) => mockRerunMission(...args),
  synthesizeMissionReport: (...args: unknown[]) =>
    mockSynthesizeMissionReport(...args),
}));

// ── Import page under test (after mocks) ─────────────────────────────

import MissionDetailPage from "@/app/missions/[missionId]/page";

// ── Helpers ──────────────────────────────────────────────────────────

function setupDefaultMocks() {
  mockFetchMissionStatus.mockResolvedValue(makeMissionStatus());
  mockFetchMissionFindings.mockResolvedValue({
    items: [makeFinding()],
    total: 1,
  });
  mockFetchRunSteps.mockResolvedValue([]);
  mockStartMission.mockResolvedValue({});
  mockStopMission.mockResolvedValue({});
  mockRerunMission.mockResolvedValue({});
  mockSynthesizeMissionReport.mockResolvedValue({
    report: { id: "report-1" },
  });
}

// ── Tests ────────────────────────────────────────────────────────────

describe("MissionDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupDefaultMocks();
  });

  // ── Loading state ──────────────────────────────────────────────────

  it("renders skeleton while loading", () => {
    // Make the API hang so we see the loading state
    mockFetchMissionStatus.mockReturnValue(new Promise(() => {}));
    mockFetchMissionFindings.mockReturnValue(new Promise(() => {}));

    render(<MissionDetailPage />);

    const skeleton = document.querySelector(".animate-pulse");
    expect(skeleton).toBeInTheDocument();
  });

  // ── Error state ────────────────────────────────────────────────────

  it("shows error panel with retry button on fetch failure", async () => {
    mockFetchMissionStatus.mockRejectedValue(new Error("Network fail"));

    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Network fail")).toBeInTheDocument();
    });

    expect(screen.getByText("Try again")).toBeInTheDocument();
  });

  it("retry button re-fetches data", async () => {
    // Reject all calls so the WS reconnect effect also fails
    mockFetchMissionStatus.mockRejectedValue(new Error("Network fail"));

    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Try again")).toBeInTheDocument();
    });

    // Reset to success for retry
    mockFetchMissionStatus.mockResolvedValue(makeMissionStatus());
    mockFetchMissionFindings.mockResolvedValue({
      items: [makeFinding()],
      total: 1,
    });

    fireEvent.click(screen.getByText("Try again"));

    await waitFor(() => {
      expect(screen.getByText("Mission")).toBeInTheDocument();
    });
  });

  // ── Mission header ─────────────────────────────────────────────────

  it("renders mission header with status badge", async () => {
    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Mission")).toBeInTheDocument();
    });

    // Status badge
    expect(screen.getByText("completed")).toBeInTheDocument();
    // Findings count
    expect(screen.getByText(/3 findings/)).toBeInTheDocument();
    // Confidence
    expect(screen.getByText(/85% confidence/)).toBeInTheDocument();
  });

  // ── Thinking indicator ─────────────────────────────────────────────

  it("renders thinking indicator when mission is running", async () => {
    mockFetchMissionStatus.mockResolvedValue(
      makeMissionStatus({
        status: "running",
        activities: [
          {
            id: "a1",
            activity_type: "searching",
            content: "Looking for data",
            metadata: { agent_name: "Researcher" },
            confidence: null,
            created_at: null,
          },
        ],
      }),
    );

    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Researcher")).toBeInTheDocument();
    });

    expect(screen.getByText("searching")).toBeInTheDocument();
  });

  // ── Tabs ───────────────────────────────────────────────────────────

  it('shows "Live Activity" tab by default', async () => {
    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Live Activity")).toBeInTheDocument();
    });

    const activityTab = screen.getByRole("tab", { name: /Live Activity/i });
    expect(activityTab).toHaveAttribute("aria-selected", "true");
  });

  it("switching tabs shows Findings content", async () => {
    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Live Activity")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("tab", { name: /Findings/ }));

    await waitFor(() => {
      expect(
        screen.getByRole("tabpanel", { name: /Findings/i }),
      ).toBeInTheDocument();
    });

    // Finding content should be visible
    expect(screen.getByText("Finding 1")).toBeInTheDocument();
  });

  it("switching tabs shows Structured Data content", async () => {
    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Live Activity")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("tab", { name: /Structured Data/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("tabpanel", { name: /Structured Data/i }),
      ).toBeInTheDocument();
    });
  });

  // ── Activity feed ──────────────────────────────────────────────────

  it("activity feed shows stream-in items", async () => {
    mockFetchMissionStatus.mockResolvedValue(
      makeMissionStatus({
        activities: [
          {
            id: "a1",
            activity_type: "searching",
            content: "Searching for market data",
            metadata: {},
            confidence: null,
            created_at: "2026-01-01T00:00:00Z",
          },
          {
            id: "a2",
            activity_type: "analyzing",
            content: "Analyzing trends",
            metadata: {},
            confidence: null,
            created_at: "2026-01-01T00:01:00Z",
          },
        ],
      }),
    );

    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(
        screen.getByText("Searching for market data"),
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Analyzing trends")).toBeInTheDocument();

    // Items have the stream-in CSS class
    const streamInItems = document.querySelectorAll(".stream-in");
    expect(streamInItems.length).toBeGreaterThanOrEqual(2);
  });

  // ── Synthesize report ──────────────────────────────────────────────

  it('"Structure Findings into Synthesized Report" button appears when completed + has findings', async () => {
    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(
        screen.getByText("Structure Findings into Synthesized Report"),
      ).toBeInTheDocument();
    });
  });

  it("synthesize button does not appear when status is running", async () => {
    mockFetchMissionStatus.mockResolvedValue(
      makeMissionStatus({ status: "running" }),
    );

    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Mission")).toBeInTheDocument();
    });

    expect(
      screen.queryByText("Structure Findings into Synthesized Report"),
    ).not.toBeInTheDocument();
  });

  it("synthesize button does not appear when no findings", async () => {
    mockFetchMissionFindings.mockResolvedValue({ items: [], total: 0 });

    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Mission")).toBeInTheDocument();
    });

    expect(
      screen.queryByText("Structure Findings into Synthesized Report"),
    ).not.toBeInTheDocument();
  });

  it("synthesize button calls the API and shows success state", async () => {
    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(
        screen.getByText("Structure Findings into Synthesized Report"),
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByText("Structure Findings into Synthesized Report"),
    );

    await waitFor(() => {
      expect(mockSynthesizeMissionReport).toHaveBeenCalledWith(
        "test-mission-id",
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText("Report generated successfully"),
      ).toBeInTheDocument();
    });
  });

  // ── Continue Research ──────────────────────────────────────────────

  it('"Continue Research" section appears when done with findings', async () => {
    // Need findings with multiple categories/tags to generate suggestions
    mockFetchMissionFindings.mockResolvedValue({
      items: [
        makeFinding({ id: "f1", category: "market", tags: ["tag-a", "tag-b"] }),
        makeFinding({ id: "f2", category: "competitor", tags: ["tag-c"] }),
      ],
      total: 2,
    });

    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Continue Research")).toBeInTheDocument();
    });
  });

  it("Continue Research does not appear when mission is running", async () => {
    mockFetchMissionStatus.mockResolvedValue(
      makeMissionStatus({ status: "running" }),
    );

    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Mission")).toBeInTheDocument();
    });

    expect(screen.queryByText("Continue Research")).not.toBeInTheDocument();
  });

  // ── Tab accessibility ──────────────────────────────────────────────

  it('tab buttons have role="tab" and aria-selected', async () => {
    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Live Activity")).toBeInTheDocument();
    });

    const tabs = screen.getAllByRole("tab");
    expect(tabs.length).toBe(3);

    // Only the activity tab should be selected initially
    const activityTab = tabs.find((t) => t.textContent?.includes("Live Activity"));
    expect(activityTab).toHaveAttribute("aria-selected", "true");

    const findingsTab = tabs.find((t) => t.textContent?.includes("Findings"));
    expect(findingsTab).toHaveAttribute("aria-selected", "false");
  });

  it('tab panels have role="tabpanel"', async () => {
    render(<MissionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Live Activity")).toBeInTheDocument();
    });

    // Activity tabpanel is visible by default
    expect(
      screen.getByRole("tabpanel", { name: /Live Activity/i }),
    ).toBeInTheDocument();

    // Switch to Findings
    fireEvent.click(screen.getByRole("tab", { name: /Findings/ }));

    await waitFor(() => {
      expect(
        screen.getByRole("tabpanel", { name: /Findings/i }),
      ).toBeInTheDocument();
    });
  });
});
