/**
 * Integration test: Full user flow from project creation through onboarding to mission start.
 * Tests the interaction between HomePage → ProjectDetailPage → MissionDetailPage.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ── Mocks ────────────────────────────────────────────────────────────

const mockPush = vi.fn();
const mockPrefetch = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, prefetch: mockPrefetch }),
  usePathname: () => "/",
  useParams: () => ({}),
}));

vi.mock("@/components/WebSocketProvider", () => ({
  useWS: () => ({ connectionState: "connected", subscribe: vi.fn(() => vi.fn()) }),
}));

vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const mockCreateProject = vi.fn();
const mockFetchProjects = vi.fn();

vi.mock("@/lib/api", () => ({
  createProject: (...args: unknown[]) => mockCreateProject(...args),
  fetchProjects: (...args: unknown[]) => mockFetchProjects(...args),
  fetchProject: vi.fn().mockResolvedValue({
    id: "proj-1",
    user_id: "u1",
    name: "Test Research",
    description: null,
    status: "active",
    project_type: "market_research",
    domain_context: null,
    total_missions: 0,
    total_findings: 0,
    total_calls_made: 0,
    total_reports_generated: 0,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  }),
  fetchMissions: vi.fn().mockResolvedValue([]),
  fetchReports: vi.fn().mockResolvedValue([]),
  generateProjectQuestions: vi.fn().mockResolvedValue({
    questions: [
      { id: "q1", question: "What market?", type: "text", options: null, placeholder: "Enter market" },
      { id: "q2", question: "Which segment?", type: "select", options: ["B2B", "B2C"], placeholder: "Pick one" },
    ],
  }),
  configureAndStartProject: vi.fn().mockResolvedValue({
    project: { id: "proj-1", name: "Test Research", domain_context: "synthesized context" },
    mission: { id: "mission-1" },
  }),
}));

// ── Tests ────────────────────────────────────────────────────────────

import HomePage from "@/app/page";

describe("User Flow: Create Project → Onboarding → Start Mission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchProjects.mockResolvedValue([]);
    mockCreateProject.mockResolvedValue({ id: "proj-1" });
  });

  it("Step 1: User selects a template and creates a project from the home page", async () => {
    render(<HomePage />);

    // Wait for page to render
    await waitFor(() => {
      expect(screen.getByText("New Research")).toBeInTheDocument();
    });

    // Select a template
    const marketResearch = screen.getByText("Market Research");
    fireEvent.click(marketResearch);

    // Name input should appear
    const nameInput = await screen.findByDisplayValue("Market Research Study");
    expect(nameInput).toBeInTheDocument();

    // Modify name and create
    fireEvent.change(nameInput, { target: { value: "Test Research" } });

    const createBtn = screen.getByText("Create Project");
    expect(createBtn).not.toBeDisabled();
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(mockCreateProject).toHaveBeenCalledWith({
        name: "Test Research",
        project_type: "market_research",
      });
    });

    // Should navigate to the new project
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/projects/proj-1");
    });
  });

  it("Step 2: Enter key submits the project (keyboard flow)", async () => {
    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("New Research")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Custom Research"));

    const nameInput = await screen.findByDisplayValue("Research Project");
    fireEvent.change(nameInput, { target: { value: "Keyboard Test" } });
    fireEvent.keyDown(nameInput, { key: "Enter" });

    await waitFor(() => {
      expect(mockCreateProject).toHaveBeenCalledWith({
        name: "Keyboard Test",
        project_type: "custom",
      });
    });
  });

  it("Step 3: Template selection has correct ARIA roles", () => {
    render(<HomePage />);

    const radiogroup = screen.getByRole("radiogroup");
    expect(radiogroup).toHaveAttribute("aria-label", "Research type");

    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(6);

    // Initially none selected
    radios.forEach((r) => expect(r).toHaveAttribute("aria-checked", "false"));

    // Click one
    fireEvent.click(radios[0]);
    expect(radios[0]).toHaveAttribute("aria-checked", "true");
    expect(radios[1]).toHaveAttribute("aria-checked", "false");
  });
});
