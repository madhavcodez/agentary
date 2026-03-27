import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '@/lib/hooks/useWebSocket'

// ── Mock localStorage ──────────────────────────────────────────────

const mockStorage: Record<string, string> = {}
const localStorageMock = {
  getItem: vi.fn((key: string) => mockStorage[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    mockStorage[key] = value
  }),
  removeItem: vi.fn((key: string) => {
    delete mockStorage[key]
  }),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// ── Mock WebSocket ────────────────────────────────────────────────

interface MockWS {
  url: string
  onopen: ((ev: Event) => void) | null
  onmessage: ((ev: MessageEvent) => void) | null
  onerror: ((ev: Event) => void) | null
  onclose: ((ev: CloseEvent) => void) | null
  readyState: number
  close: ReturnType<typeof vi.fn>
  send: ReturnType<typeof vi.fn>
}

let mockWSInstance: MockWS | null = null
const mockWSInstances: MockWS[] = []

class MockWebSocket {
  static OPEN = 1
  static CLOSED = 3

  url: string
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  readyState = MockWebSocket.OPEN
  close = vi.fn()
  send = vi.fn()

  constructor(url: string) {
    this.url = url
    mockWSInstance = this as unknown as MockWS
    mockWSInstances.push(this as unknown as MockWS)
  }
}

// ── Setup / Teardown ──────────────────────────────────────────────

beforeEach(() => {
  vi.useFakeTimers()
  mockWSInstance = null
  mockWSInstances.length = 0
  mockStorage['agentary_token'] = 'test-jwt-token'
  vi.stubGlobal('WebSocket', MockWebSocket)
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  Object.keys(mockStorage).forEach((key) => delete mockStorage[key])
})

// ── Tests ─────────────────────────────────────────────────────────

describe('useWebSocket', () => {
  it('starts in connecting state when enabled', () => {
    const { result } = renderHook(() => useWebSocket({ enabled: true }))
    // Before WebSocket.onopen fires, state should be "connecting"
    expect(result.current.connectionState).toBe('connecting')
  })

  it('transitions to connected on WebSocket open', () => {
    const { result } = renderHook(() => useWebSocket({ enabled: true }))

    // Simulate WebSocket open
    act(() => {
      if (mockWSInstance?.onopen) {
        mockWSInstance.onopen(new Event('open'))
      }
    })

    expect(result.current.connectionState).toBe('connected')
  })

  it('does not connect when enabled is false', () => {
    renderHook(() => useWebSocket({ enabled: false }))
    expect(mockWSInstance).toBeNull()
  })

  it('does not connect when no token is present', () => {
    delete mockStorage['agentary_token']
    renderHook(() => useWebSocket({ enabled: true }))
    expect(mockWSInstance).toBeNull()
  })

  it('connects to correct URL without projectId', () => {
    renderHook(() => useWebSocket({ enabled: true }))
    expect(mockWSInstance).not.toBeNull()
    expect(mockWSInstance!.url).toContain('/ws/live-feed')
    expect(mockWSInstance!.url).toContain('token=test-jwt-token')
  })

  it('connects to project-specific URL with projectId', () => {
    renderHook(() =>
      useWebSocket({ enabled: true, projectId: 'proj-123' }),
    )
    expect(mockWSInstance).not.toBeNull()
    expect(mockWSInstance!.url).toContain('/api/live-feed/proj-123')
  })

  it('subscribe returns an unsubscribe function', () => {
    const { result } = renderHook(() => useWebSocket({ enabled: true }))
    const handler = vi.fn()
    const unsubscribe = result.current.subscribe('test.event', handler)
    expect(typeof unsubscribe).toBe('function')
  })

  it('dispatches events to subscribed handlers', () => {
    const handler = vi.fn()
    const { result } = renderHook(() => useWebSocket({ enabled: true }))

    act(() => {
      result.current.subscribe('agent.thinking', handler)
    })

    // Simulate incoming message
    act(() => {
      if (mockWSInstance?.onmessage) {
        const event = new MessageEvent('message', {
          data: JSON.stringify({
            event_type: 'agent.thinking',
            data: { agent: 'researcher' },
            timestamp: new Date().toISOString(),
          }),
        })
        mockWSInstance.onmessage(event)
      }
    })

    expect(handler).toHaveBeenCalledTimes(1)
    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({ event_type: 'agent.thinking' }),
    )
  })

  it('does not dispatch to handler after unsubscribe', () => {
    const handler = vi.fn()
    const { result } = renderHook(() => useWebSocket({ enabled: true }))

    let unsub: () => void = () => {}
    act(() => {
      unsub = result.current.subscribe('test.event', handler)
    })

    act(() => {
      unsub()
    })

    // Simulate message after unsubscribe
    act(() => {
      if (mockWSInstance?.onmessage) {
        const event = new MessageEvent('message', {
          data: JSON.stringify({
            event_type: 'test.event',
            data: {},
            timestamp: new Date().toISOString(),
          }),
        })
        mockWSInstance.onmessage(event)
      }
    })

    expect(handler).not.toHaveBeenCalled()
  })

  it('dispatches to wildcard handlers', () => {
    const wildcardHandler = vi.fn()
    const { result } = renderHook(() => useWebSocket({ enabled: true }))

    act(() => {
      result.current.subscribe('*', wildcardHandler)
    })

    act(() => {
      if (mockWSInstance?.onmessage) {
        const event = new MessageEvent('message', {
          data: JSON.stringify({
            event_type: 'any.event',
            data: {},
            timestamp: new Date().toISOString(),
          }),
        })
        mockWSInstance.onmessage(event)
      }
    })

    expect(wildcardHandler).toHaveBeenCalledTimes(1)
  })

  it('calls onEvent callback for all events', () => {
    const onEvent = vi.fn()
    renderHook(() => useWebSocket({ enabled: true, onEvent }))

    act(() => {
      if (mockWSInstance?.onmessage) {
        const event = new MessageEvent('message', {
          data: JSON.stringify({
            event_type: 'finding.created',
            data: {},
            timestamp: new Date().toISOString(),
          }),
        })
        mockWSInstance.onmessage(event)
      }
    })

    expect(onEvent).toHaveBeenCalledTimes(1)
  })

  it('ignores pong messages', () => {
    const onEvent = vi.fn()
    renderHook(() => useWebSocket({ enabled: true, onEvent }))

    act(() => {
      if (mockWSInstance?.onmessage) {
        const event = new MessageEvent('message', {
          data: JSON.stringify({
            event_type: 'pong',
            data: {},
            timestamp: new Date().toISOString(),
          }),
        })
        mockWSInstance.onmessage(event)
      }
    })

    expect(onEvent).not.toHaveBeenCalled()
  })

  it('attempts reconnection on close', () => {
    renderHook(() => useWebSocket({ enabled: true }))

    // Simulate open then close
    act(() => {
      if (mockWSInstance?.onopen) {
        mockWSInstance.onopen(new Event('open'))
      }
    })

    const firstInstance = mockWSInstance

    act(() => {
      if (firstInstance?.onclose) {
        firstInstance.onclose(new CloseEvent('close'))
      }
    })

    // Advance timer to trigger reconnect
    act(() => {
      vi.advanceTimersByTime(2000)
    })

    // A new WebSocket instance should have been created
    expect(mockWSInstances.length).toBeGreaterThan(1)
  })

  it('closes WebSocket on unmount', () => {
    const { unmount } = renderHook(() =>
      useWebSocket({ enabled: true }),
    )

    const instance = mockWSInstance
    unmount()

    expect(instance?.close).toHaveBeenCalled()
  })
})
