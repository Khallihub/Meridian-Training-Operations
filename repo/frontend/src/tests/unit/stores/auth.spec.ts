import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock the auth API
vi.mock('@/api/endpoints/auth', () => ({
  authApi: {
    login: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  },
}))

import { authApi } from '@/api/endpoints/auth'

// Minimal JWT with role payload
function makeToken(role: string) {
  const payload = btoa(JSON.stringify({ sub: 'user-1', role, exp: 9999999999, iat: 0 }))
  return `header.${payload}.sig`
}

describe('authStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('login stores token and decodes role', async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: makeToken('admin'),
      refresh_token: 'rt',
    })
    const store = useAuthStore()
    await store.login('admin', 'pass')
    expect(store.isAuthenticated).toBe(true)
    expect(store.role).toBe('admin')
    expect(store.isAdmin).toBe(true)
    expect(localStorage.getItem('refresh_token')).toBe('rt')
  })

  it('logout clears state', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: makeToken('learner'), refresh_token: 'rt' })
    vi.mocked(authApi.logout).mockResolvedValue(undefined)
    const store = useAuthStore()
    await store.login('x', 'y')
    await store.logout()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })

  it('refresh rotates access token', async () => {
    localStorage.setItem('refresh_token', 'old-rt')
    vi.mocked(authApi.refresh).mockResolvedValue({ access_token: makeToken('instructor'), refresh_token: 'new-rt' })
    const store = useAuthStore()
    const newToken = await store.refresh()
    expect(store.accessToken).toBeTruthy()
    expect(localStorage.getItem('refresh_token')).toBe('new-rt')
  })

  it('computeds reflect correct role', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: makeToken('finance'), refresh_token: 'rt' })
    const store = useAuthStore()
    await store.login('x', 'y')
    expect(store.isFinance).toBe(true)
    expect(store.isAdmin).toBe(false)
    expect(store.isLearner).toBe(false)
  })
})
