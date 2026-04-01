import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// ── Mocks ────────────────────────────────────────────────────────

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

const mockFetchProjects = vi.fn()
const mockCreateProject = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchProjects: (...args: unknown[]) => mockFetchProjects(...args),
  createProject: (...args: unknown[]) => mockCreateProject(...args),
}))

const mockToast = vi.fn()

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({ toast: mockToast }),
}))

import HomePage from '@/app/page'

// ── Tests ────────────────────────────────────────────────────────

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProjects.mockResolvedValue([])
  })

  it('renders "New Research" heading', async () => {
    render(<HomePage />)

    await waitFor(() => {
      expect(screen.getByText('New Research')).toBeInTheDocument()
    })
  })

  it('renders all 6 template options', async () => {
    render(<HomePage />)

    await waitFor(() => {
      expect(screen.getByText('Real Estate')).toBeInTheDocument()
    })

    expect(screen.getByText('Competitive Intel')).toBeInTheDocument()
    expect(screen.getByText('Market Research')).toBeInTheDocument()
    expect(screen.getByText('Due Diligence')).toBeInTheDocument()
    expect(screen.getByText('Local Business')).toBeInTheDocument()
    expect(screen.getByText('Custom Research')).toBeInTheDocument()
  })

  it('selecting a template shows the name input', async () => {
    render(<HomePage />)

    await waitFor(() => {
      expect(screen.getByText('Real Estate')).toBeInTheDocument()
    })

    // Name input should not exist before selection
    expect(screen.queryByLabelText('Project name')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Real Estate'))

    // After selection, the input and Create button should appear
    expect(screen.getByLabelText('Project name')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Create Project/i }),
    ).toBeInTheDocument()
  })

  it('Create button is disabled when name is empty', async () => {
    render(<HomePage />)

    await waitFor(() => {
      expect(screen.getByText('Real Estate')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Real Estate'))

    const input = screen.getByLabelText('Project name')
    // Clear the autofilled name suggestion
    fireEvent.change(input, { target: { value: '' } })

    const createButton = screen.getByRole('button', {
      name: /Create Project/i,
    })
    expect(createButton).toBeDisabled()
  })

  it('Enter key does not fire handleCreate when creating is true', async () => {
    // Simulate a create that never resolves (stays in "creating" state)
    mockCreateProject.mockReturnValue(new Promise(() => {}))

    render(<HomePage />)

    await waitFor(() => {
      expect(screen.getByText('Real Estate')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Real Estate'))

    const input = screen.getByLabelText('Project name')

    // First Enter triggers the create
    fireEvent.keyDown(input, { key: 'Enter' })

    // Now "creating" is true -- the button text changes
    await waitFor(() => {
      expect(screen.getByText('Creating...')).toBeInTheDocument()
    })

    // Second Enter should be guarded by the `!creating` check
    mockCreateProject.mockClear()
    fireEvent.keyDown(input, { key: 'Enter' })

    // The mock should NOT have been called a second time
    expect(mockCreateProject).not.toHaveBeenCalled()
  })

  it('navigates to the new project on successful create', async () => {
    mockCreateProject.mockResolvedValue({ id: 'new-proj-123' })

    render(<HomePage />)

    await waitFor(() => {
      expect(screen.getByText('Real Estate')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Real Estate'))

    const createButton = screen.getByRole('button', {
      name: /Create Project/i,
    })
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/projects/new-proj-123')
    })
  })
})
