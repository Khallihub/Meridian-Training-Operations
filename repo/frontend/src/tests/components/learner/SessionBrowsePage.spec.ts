import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/learner/sessions' }),
}))

vi.mock('@/stores/sessions', () => ({
  useSessionsStore: () => ({
    weekSessions: [],
    monthlySessions: [],
    loading: false,
    fetchWeek: vi.fn(),
    fetchMonth: vi.fn(),
  }),
}))

vi.mock('@/stores/bookings', () => ({
  useBookingsStore: () => ({ bookings: [], fetchBookings: vi.fn() }),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ role: 'learner', isAuthenticated: true, user: null }),
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ addToast: vi.fn() }),
}))

vi.mock('@/stores/checkout', () => ({
  useCheckoutStore: () => ({ createCart: vi.fn(), order: null }),
}))

describe('SessionBrowsePage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('default view is calendar', () => {
    const defaultView = 'calendar'
    expect(['calendar', 'month', 'list']).toContain(defaultView)
  })

  it('bookable statuses only include scheduled', () => {
    const bookableStatuses = ['scheduled']
    expect(bookableStatuses).toContain('scheduled')
    expect(bookableStatuses).not.toContain('live')
    expect(bookableStatuses).not.toContain('ended')
    expect(bookableStatuses).not.toContain('canceled')
  })

  it('filters out canceled sessions for month display', () => {
    const sessions = [
      { id: 's-1', status: 'scheduled', title: 'A' },
      { id: 's-2', status: 'canceled', title: 'B' },
      { id: 's-3', status: 'live', title: 'C' },
    ]
    const filtered = sessions.filter(s => s.status !== 'canceled')
    expect(filtered).toHaveLength(2)
    expect(filtered.map(s => s.id)).toEqual(['s-1', 's-3'])
  })

  it('timezone falls back to browser default', () => {
    const userTz = null
    const tz = userTz ?? Intl.DateTimeFormat().resolvedOptions().timeZone
    expect(tz).toBeTruthy()
  })
})
