import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWebSocket } from '@/composables/useWebSocket'

// Mock auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ accessToken: 'mock-token' }),
}))

let mockWs: any
const MockWebSocket = vi.fn().mockImplementation(() => {
  mockWs = { send: vi.fn(), close: vi.fn(), onopen: null, onmessage: null, onerror: null, onclose: null }
  return mockWs
})

describe('useWebSocket', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    (globalThis as any).WebSocket = MockWebSocket as any
    MockWebSocket.mockClear()
  })

  it('connects on creation', () => {
    useWebSocket('session-1')
    expect(MockWebSocket).toHaveBeenCalledWith(expect.stringContaining('session-1'))
    expect(MockWebSocket).toHaveBeenCalledWith(expect.stringContaining('mock-token'))
  })

  it('handles room_state snapshot', () => {
    const { roomState } = useWebSocket('session-1')
    mockWs.onopen?.()
    mockWs.onmessage?.({ data: JSON.stringify({ type: 'room_state', session_status: 'live', enrolled_count: 18, checked_in_count: 12 }) })
    expect(roomState.value?.session_status).toBe('live')
    expect(roomState.value?.enrolled_count).toBe(18)
    expect(roomState.value?.checked_in_count).toBe(12)
  })

  it('increments checked_in_count on attendee_joined', () => {
    const { roomState } = useWebSocket('session-1')
    mockWs.onmessage?.({ data: JSON.stringify({ type: 'room_state', session_status: 'live', enrolled_count: 10, checked_in_count: 5 }) })
    mockWs.onmessage?.({ data: JSON.stringify({ type: 'attendee_joined' }) })
    expect(roomState.value?.checked_in_count).toBe(6)
  })

  it('decrements checked_in_count on attendee_left', () => {
    const { roomState } = useWebSocket('session-1')
    mockWs.onmessage?.({ data: JSON.stringify({ type: 'room_state', session_status: 'live', enrolled_count: 10, checked_in_count: 5 }) })
    mockWs.onmessage?.({ data: JSON.stringify({ type: 'attendee_left' }) })
    expect(roomState.value?.checked_in_count).toBe(4)
  })

  it('reconnects on non-1000 close', () => {
    vi.useFakeTimers()
    useWebSocket('session-1')
    mockWs.onclose?.({ code: 1006 })
    vi.advanceTimersByTime(1500)
    expect(MockWebSocket).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })

  it('disconnect prevents reconnect', () => {
    vi.useFakeTimers()
    const { disconnect } = useWebSocket('session-1')
    disconnect()
    mockWs.onclose?.({ code: 1006 })
    vi.advanceTimersByTime(5000)
    expect(MockWebSocket).toHaveBeenCalledTimes(1) // no reconnect
    vi.useRealTimers()
  })
})
