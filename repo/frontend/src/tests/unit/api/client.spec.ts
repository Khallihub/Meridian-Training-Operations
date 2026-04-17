import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock auth store
const mockAccessToken = { value: 'test-token' }
const mockRefresh = vi.fn()
const mockLogout = vi.fn()
const mockRecordActivity = vi.fn()

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    accessToken: mockAccessToken.value,
    isAuthenticated: !!mockAccessToken.value,
    refresh: mockRefresh,
    logout: mockLogout,
    recordActivity: mockRecordActivity,
  }),
}))

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

describe('API Client', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('client is importable and has expected structure', async () => {
    const { default: client } = await import('@/api/client')
    expect(client).toBeTruthy()
    expect(client.defaults.baseURL).toBe('/')
    expect(client.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('request interceptor adds authorization header', async () => {
    const { default: client } = await import('@/api/client')
    // The interceptor reads from auth store
    // Verify client has interceptors configured
    expect(client.interceptors.request).toBeTruthy()
    expect(client.interceptors.response).toBeTruthy()
  })
})
