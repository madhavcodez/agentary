import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

// ── Mocks ────────────────────────────────────────────────────────

let mockPathname = '/'

vi.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
}))

vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode
    href: string
    [key: string]: unknown
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}))

vi.mock('@/components/WebSocketProvider', () => ({
  useWS: () => ({
    connectionState: 'connected',
    subscribe: vi.fn(() => vi.fn()),
  }),
}))

import Nav from '@/components/Nav'

// ── Tests ────────────────────────────────────────────────────────

describe('Nav sidebar', () => {
  beforeEach(() => {
    mockPathname = '/'
  })

  it('renders all 3 section titles', () => {
    render(<Nav />)

    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Work')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
  })

  it('renders correct items in Overview section', () => {
    render(<Nav />)

    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Projects')).toBeInTheDocument()
  })

  it('renders correct items in Work section', () => {
    render(<Nav />)

    expect(screen.getByText('Missions')).toBeInTheDocument()
    expect(screen.getByText('Reports')).toBeInTheDocument()
    expect(screen.getByText('Workflows')).toBeInTheDocument()
  })

  it('renders correct items in System section', () => {
    render(<Nav />)

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Monitors')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('Dashboard is in the System section (not Overview)', () => {
    render(<Nav />)

    // The System section title comes after Work section's items.
    // Dashboard link should be grouped after the "System" heading.
    const systemHeading = screen.getByText('System')
    const dashboardLink = screen.getByText('Dashboard')

    // Both should share the same section parent container
    const systemSection = systemHeading.closest('div')!
    expect(systemSection).toContainElement(dashboardLink)
  })

  it('applies active state (aria-current="page") for matching pathname', () => {
    mockPathname = '/projects'
    render(<Nav />)

    const projectsLink = screen.getByText('Projects').closest('a')!
    expect(projectsLink).toHaveAttribute('aria-current', 'page')

    // Home should not be active when on /projects
    const homeLink = screen.getByText('Home').closest('a')!
    expect(homeLink).not.toHaveAttribute('aria-current')
  })

  it('applies active state for root path only to Home', () => {
    mockPathname = '/'
    render(<Nav />)

    const homeLink = screen.getByText('Home').closest('a')!
    expect(homeLink).toHaveAttribute('aria-current', 'page')

    const projectsLink = screen.getByText('Projects').closest('a')!
    expect(projectsLink).not.toHaveAttribute('aria-current')
  })

  it('applies active state for nested paths', () => {
    mockPathname = '/projects/some-id'
    render(<Nav />)

    const projectsLink = screen.getByText('Projects').closest('a')!
    expect(projectsLink).toHaveAttribute('aria-current', 'page')
  })

  it('renders connection status dot with "Connected" label', () => {
    render(<Nav />)

    expect(screen.getByText('Connected')).toBeInTheDocument()
  })
})
