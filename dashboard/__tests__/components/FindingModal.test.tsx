import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FindingModal from '@/components/ui/FindingModal'
import type { MissionFinding } from '@/lib/types'

// ── Mock security module ─────────────────────────────────────────

vi.mock('@/lib/security', () => ({
  sanitizeUrl: (url: string | null | undefined) => {
    if (!url) return null
    try {
      const parsed = new URL(url)
      if (!['https:', 'http:'].includes(parsed.protocol)) return null
      return url
    } catch {
      return null
    }
  },
}))

// ── Fixtures ─────────────────────────────────────────────────────

function makeFinding(overrides: Partial<MissionFinding> = {}): MissionFinding {
  return {
    id: 'finding-1',
    category: 'Market Trend',
    title: 'Median Home Prices Rising',
    content: 'Detailed content about housing market trends.',
    structured_data: null,
    source_type: 'web',
    source_url: null,
    source_name: null,
    confidence: 0.85,
    verified: false,
    tags: [],
    created_at: '2025-01-15T10:00:00Z',
    ...overrides,
  }
}

function makeRelatedFinding(id: string, title: string): MissionFinding {
  return makeFinding({ id, title, confidence: 0.72 })
}

// ── Tests ────────────────────────────────────────────────────────

describe('FindingModal', () => {
  const onClose = vi.fn<() => void>()

  beforeEach(() => {
    onClose.mockClear()
  })

  it('renders finding title, category, content, and confidence bar', () => {
    const finding = makeFinding()
    render(<FindingModal finding={finding} onClose={onClose} />)

    expect(screen.getByText('Median Home Prices Rising')).toBeInTheDocument()
    expect(screen.getByText('Market Trend')).toBeInTheDocument()
    expect(
      screen.getByText('Detailed content about housing market trends.'),
    ).toBeInTheDocument()
    // Confidence is 85% High
    expect(screen.getByText('85% High')).toBeInTheDocument()
  })

  it('has role="dialog" and aria-modal="true"', () => {
    const finding = makeFinding()
    render(<FindingModal finding={finding} onClose={onClose} />)

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('calls onClose when Escape key is pressed', () => {
    const finding = makeFinding()
    render(<FindingModal finding={finding} onClose={onClose} />)

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when backdrop is clicked', () => {
    const finding = makeFinding()
    render(<FindingModal finding={finding} onClose={onClose} />)

    // The backdrop is the first child div inside the dialog container
    // It has an onClick={onClose} handler and includes the class 'absolute inset-0'
    const dialog = screen.getByRole('dialog')
    const backdrop = dialog.querySelector('.absolute.inset-0') as HTMLElement
    expect(backdrop).toBeTruthy()
    fireEvent.click(backdrop)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('renders source link when source_url is provided', () => {
    const finding = makeFinding({
      source_url: 'https://example.com/report',
      source_name: 'Example Report',
    })
    render(<FindingModal finding={finding} onClose={onClose} />)

    const sourceLink = screen.getByText('Example Report')
    expect(sourceLink).toBeInTheDocument()
    expect(sourceLink.closest('a')).toHaveAttribute(
      'href',
      'https://example.com/report',
    )
  })

  it('renders tags', () => {
    const finding = makeFinding({
      tags: ['housing', 'investment', 'growth'],
    })
    render(<FindingModal finding={finding} onClose={onClose} />)

    expect(screen.getByText('housing')).toBeInTheDocument()
    expect(screen.getByText('investment')).toBeInTheDocument()
    expect(screen.getByText('growth')).toBeInTheDocument()
    expect(screen.getByText('Tags')).toBeInTheDocument()
  })

  it('renders related findings in horizontal scroll section', () => {
    const related = [
      makeRelatedFinding('rf-1', 'Supply Chain Disruption'),
      makeRelatedFinding('rf-2', 'Interest Rate Impact'),
    ]
    const onSelectRelated = vi.fn()

    render(
      <FindingModal
        finding={makeFinding()}
        onClose={onClose}
        relatedFindings={related}
        onSelectRelated={onSelectRelated}
      />,
    )

    expect(screen.getByText('Related Findings')).toBeInTheDocument()
    expect(screen.getByText('Supply Chain Disruption')).toBeInTheDocument()
    expect(screen.getByText('Interest Rate Impact')).toBeInTheDocument()
  })

  it('calls onSelectRelated when a related finding is clicked', () => {
    const related = [makeRelatedFinding('rf-1', 'Supply Chain Disruption')]
    const onSelectRelated = vi.fn()

    render(
      <FindingModal
        finding={makeFinding()}
        onClose={onClose}
        relatedFindings={related}
        onSelectRelated={onSelectRelated}
      />,
    )

    fireEvent.click(screen.getByText('Supply Chain Disruption'))
    expect(onSelectRelated).toHaveBeenCalledTimes(1)
    expect(onSelectRelated).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'rf-1' }),
    )
  })

  it('renders structured data grid', () => {
    const finding = makeFinding({
      structured_data: {
        'Average Price': '$425,000',
        'YoY Change': '+8.2%',
      },
    })
    render(<FindingModal finding={finding} onClose={onClose} />)

    expect(screen.getByText('Structured Data')).toBeInTheDocument()
    expect(screen.getByText('Average Price')).toBeInTheDocument()
    expect(screen.getByText('$425,000')).toBeInTheDocument()
    expect(screen.getByText('YoY Change')).toBeInTheDocument()
    expect(screen.getByText('+8.2%')).toBeInTheDocument()
  })
})
