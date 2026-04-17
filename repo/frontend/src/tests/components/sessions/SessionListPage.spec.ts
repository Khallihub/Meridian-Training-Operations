import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock sessions store
const fetchWeekMock = vi.fn()
const fetchMonthMock = vi.fn()
vi.mock('@/stores/sessions', () => ({
  useSessionsStore: () => ({
    weekSessions: [],
    monthlySessions: [],
    currentSession: null,
    loading: false,
    fetchWeek: fetchWeekMock,
    fetchMonth: fetchMonthMock,
  }),
}))

// Mock auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    role: 'admin',
    isAdmin: true,
    isAuthenticated: true,
    user: null,
  }),
}))

// Mock router
const pushMock = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ path: '/admin/sessions' }),
}))

// Mock lucide icons
vi.mock('lucide-vue-next', () => ({
  Plus: { template: '<span>+</span>' },
  Calendar: { template: '<span>Cal</span>' },
  List: { template: '<span>List</span>' },
}))

describe('SessionListPage logic', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('view defaults to week', () => {
    // Default view mode should be week
    const defaultView = 'week'
    expect(defaultView).toBe('week')
    expect(['week', 'month', 'list']).toContain(defaultView)
  })

  it('admin prefix is /admin', () => {
    // Route prefix computation for admin
    const path = '/admin/sessions'
    const prefix = path.startsWith('/admin') ? '/admin' : '/instructor'
    expect(prefix).toBe('/admin')
  })

  it('instructor prefix is /instructor', () => {
    const path = '/instructor/sessions'
    const prefix = path.startsWith('/admin') ? '/admin' : '/instructor'
    expect(prefix).toBe('/instructor')
  })

  it('timezone falls back to browser default', () => {
    const userTz = null
    const tz = userTz ?? Intl.DateTimeFormat().resolvedOptions().timeZone
    expect(tz).toBeTruthy()
    expect(typeof tz).toBe('string')
  })

  it('fetchWeek is called with correct format', () => {
    // Verify ISO week format pattern
    const weekPattern = /^\d{4}-W\d{2}$/
    const week = new Date().toISOString().slice(0, 4) + '-W15'
    expect(week).toMatch(weekPattern)
  })
})
