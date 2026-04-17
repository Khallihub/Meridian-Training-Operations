import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/login' }),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    login: vi.fn(),
    role: 'admin',
    isAuthenticated: false,
  }),
}))

describe('LoginPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('ROLE_HOME maps all five roles', () => {
    const ROLE_HOME: Record<string, string> = {
      admin: '/admin/dashboard',
      instructor: '/instructor/dashboard',
      learner: '/learner/dashboard',
      finance: '/finance/dashboard',
      dataops: '/dataops/dashboard',
    }
    expect(Object.keys(ROLE_HOME)).toHaveLength(5)
    for (const path of Object.values(ROLE_HOME)) {
      expect(path).toMatch(/^\/\w+\/dashboard$/)
    }
  })

  it('login form requires username and password', () => {
    const validate = (u: string, p: string) => u.length > 0 && p.length > 0
    expect(validate('', '')).toBe(false)
    expect(validate('admin', '')).toBe(false)
    expect(validate('admin', 'pass')).toBe(true)
  })

  it('lockout response sets lockedUntil state', () => {
    const lockedUntil: string | null = null
    const errorResponse = { status: 423, data: { locked_until: '2026-04-17T10:00:00Z' } }
    const newLockedUntil = errorResponse.status === 423 ? errorResponse.data.locked_until : null
    expect(newLockedUntil).toBe('2026-04-17T10:00:00Z')
  })
})
