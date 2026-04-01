import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { Project, Mission } from '@/lib/types'

// ── Mocks ────────────────────────────────────────────────────────

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'proj-1' }),
  useRouter: () => ({ push: mockPush }),
}))

const mockToast = vi.fn()

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({ toast: mockToast }),
}))

const mockFetchProject = vi.fn()
const mockFetchMissions = vi.fn()
const mockFetchReports = vi.fn()
const mockCreateMission = vi.fn()
const mockGenerateProjectQuestions = vi.fn()
const mockConfigureAndStartProject = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchProject: (...args: unknown[]) => mockFetchProject(...args),
  fetchMissions: (...args: unknown[]) => mockFetchMissions(...args),
  fetchReports: (...args: unknown[]) => mockFetchReports(...args),
  createMission: (...args: unknown[]) => mockCreateMission(...args),
  generateProjectQuestions: (...args: unknown[]) =>
    mockGenerateProjectQuestions(...args),
  configureAndStartProject: (...args: unknown[]) =>
    mockConfigureAndStartProject(...args),
}))

import ProjectDetailPage from '@/app/projects/[id]/page'

// ── Fixtures ─────────────────────────────────────────────────────

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'proj-1',
    user_id: 'user-1',
    name: 'Test Project',
    description: null,
    status: 'active',
    project_type: 'real_estate',
    domain_context: null,
    total_missions: 0,
    total_findings: 0,
    total_calls_made: 0,
    total_reports_generated: 0,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    ...overrides,
  }
}

function makeMission(overrides: Partial<Mission> = {}): Mission {
  return {
    id: 'mission-1',
    project_id: 'proj-1',
    user_id: 'user-1',
    name: 'Analyze downtown pricing',
    description: null,
    objective: null,
    status: 'running',
    mission_type: 'research',
    findings_count: 12,
    confidence_score: 0.82,
    started_at: '2025-01-02T00:00:00Z',
    completed_at: null,
    created_at: '2025-01-02T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
    ...overrides,
  }
}

// ── Tests ────────────────────────────────────────────────────────

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchReports.mockResolvedValue([])
  })

  describe('when project has 0 missions (onboarding)', () => {
    beforeEach(() => {
      mockFetchProject.mockResolvedValue(makeProject())
      mockFetchMissions.mockResolvedValue([])
    })

    it('shows OnboardingFlow when project has no missions', async () => {
      mockGenerateProjectQuestions.mockReturnValue(new Promise(() => {}))

      render(<ProjectDetailPage />)

      await waitFor(() => {
        expect(
          screen.getByText(
            'Synthesizing',
          ),
        ).toBeInTheDocument()
      })
    })

    it('shows thinking dots while loading questions', async () => {
      // Never-resolving promise keeps loading state
      mockGenerateProjectQuestions.mockReturnValue(new Promise(() => {}))

      render(<ProjectDetailPage />)

      await waitFor(() => {
        expect(
          screen.getByText(
            'Synthesizing',
          ),
        ).toBeInTheDocument()
      })

      // The spinner should be visible
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeTruthy()
    })

    it('renders questions after they load', async () => {
      mockGenerateProjectQuestions.mockResolvedValue({
        questions: [
          {
            id: 'q1',
            question: 'What area are you targeting?',
            type: 'text',
            options: null,
            placeholder: 'e.g., Downtown Austin',
          },
          {
            id: 'q2',
            question: 'Property type?',
            type: 'select',
            options: ['Residential', 'Commercial', 'Industrial'],
            placeholder: 'Select type',
          },
        ],
      })

      render(<ProjectDetailPage />)

      await waitFor(() => {
        expect(
          screen.getByText('What area are you targeting?'),
        ).toBeInTheDocument()
      })

      expect(screen.getByText('Property type?')).toBeInTheDocument()
    })

    it('"Start Research" button is disabled until all questions answered', async () => {
      mockGenerateProjectQuestions.mockResolvedValue({
        questions: [
          {
            id: 'q1',
            question: 'What area are you targeting?',
            type: 'text',
            options: null,
            placeholder: 'e.g., Downtown Austin',
          },
        ],
      })

      render(<ProjectDetailPage />)

      // Wait for questions to render
      await waitFor(() => {
        expect(
          screen.getByText('What area are you targeting?'),
        ).toBeInTheDocument()
      })

      // Button text includes an em dash character
      const startButton = screen.getByRole('button', {
        name: /Start Research/i,
      })
      expect(startButton).toBeDisabled()

      // Fill in the answer
      const input = screen.getByPlaceholderText('e.g., Downtown Austin')
      fireEvent.change(input, { target: { value: 'Downtown Austin' } })

      // Now the button should be enabled
      expect(startButton).toBeEnabled()
    })
  })

  describe('when project has missions', () => {
    const missions = [
      makeMission({ id: 'mission-1', name: 'Analyze downtown pricing' }),
      makeMission({
        id: 'mission-2',
        name: 'Survey rental market',
        status: 'completed',
      }),
    ]

    beforeEach(() => {
      mockFetchProject.mockResolvedValue(
        makeProject({ total_missions: 2, total_findings: 25 }),
      )
      mockFetchMissions.mockResolvedValue(missions)
    })

    it('shows mission list instead of onboarding', async () => {
      render(<ProjectDetailPage />)

      await waitFor(() => {
        expect(
          screen.getByText('Analyze downtown pricing'),
        ).toBeInTheDocument()
      })

      expect(screen.getByText('Survey rental market')).toBeInTheDocument()

      // Onboarding should NOT be shown
      expect(
        screen.queryByText(
          'Synthesizing',
        ),
      ).not.toBeInTheDocument()
      expect(screen.queryByText('Project Setup')).not.toBeInTheDocument()
    })

    it('shows mission stats badges', async () => {
      render(<ProjectDetailPage />)

      await waitFor(() => {
        expect(screen.getByText('missions')).toBeInTheDocument()
      })

      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('25')).toBeInTheDocument()
    })

    it('clicking a mission navigates to mission page', async () => {
      render(<ProjectDetailPage />)

      await waitFor(() => {
        expect(
          screen.getByText('Analyze downtown pricing'),
        ).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Analyze downtown pricing'))

      expect(mockPush).toHaveBeenCalledWith('/missions/mission-1')
    })
  })
})
