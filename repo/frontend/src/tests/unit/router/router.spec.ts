import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock auth store before importing router
vi.mock('@/stores/auth', () => {
  const { ref, computed } = require('vue')
  let _token = ref<string | null>(null)
  let _role = ref<string | null>(null)
  return {
    useAuthStore: () => ({
      accessToken: _token,
      role: _role,
      isAuthenticated: computed(() => !!_token.value),
      isAdmin: computed(() => _role.value === 'admin'),
      isLearner: computed(() => _role.value === 'learner'),
      isFinance: computed(() => _role.value === 'finance'),
      restoreSession: vi.fn(),
      login: vi.fn(async () => {
        _token.value = 'mock-token'
        _role.value = 'admin'
      }),
      logout: vi.fn(async () => {
        _token.value = null
        _role.value = null
      }),
      _setRole: (r: string | null) => { _role.value = r; _token.value = r ? 'mock' : null },
    }),
  }
})

describe('Router configuration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('has login route marked as public', async () => {
    const { default: router } = await import('@/router/index')
    const loginRoute = router.getRoutes().find(r => r.path === '/login')
    expect(loginRoute).toBeTruthy()
    expect(loginRoute!.meta.public).toBe(true)
  })

  it('has 403 route marked as public', async () => {
    const { default: router } = await import('@/router/index')
    const forbiddenRoute = router.getRoutes().find(r => r.path === '/403')
    expect(forbiddenRoute).toBeTruthy()
    expect(forbiddenRoute!.meta.public).toBe(true)
  })

  it('admin dashboard requires admin role', async () => {
    const { default: router } = await import('@/router/index')
    const route = router.getRoutes().find(r => r.path === '/admin/dashboard')
    expect(route).toBeTruthy()
    expect(route!.meta.roles).toContain('admin')
  })

  it('learner dashboard requires learner role', async () => {
    const { default: router } = await import('@/router/index')
    const route = router.getRoutes().find(r => r.path === '/learner/dashboard')
    expect(route).toBeTruthy()
    expect(route!.meta.roles).toContain('learner')
  })

  it('finance routes require finance role', async () => {
    const { default: router } = await import('@/router/index')
    const finRoutes = router.getRoutes().filter(r => r.path.startsWith('/finance/'))
    expect(finRoutes.length).toBeGreaterThan(0)
    for (const route of finRoutes) {
      expect(route.meta.roles).toContain('finance')
    }
  })

  it('dataops routes require dataops role', async () => {
    const { default: router } = await import('@/router/index')
    const dataRoutes = router.getRoutes().filter(r => r.path.startsWith('/dataops/'))
    expect(dataRoutes.length).toBeGreaterThan(0)
    for (const route of dataRoutes) {
      expect(route.meta.roles).toContain('dataops')
    }
  })

  it('all non-public routes have roles defined', async () => {
    const { default: router } = await import('@/router/index')
    const nonPublic = router.getRoutes().filter(
      r => !r.meta.public && r.path !== '/' && !r.path.includes(':pathMatch')
    )
    for (const route of nonPublic) {
      expect(route.meta.roles, `Route ${route.path} missing roles`).toBeTruthy()
    }
  })

  it('ROLE_HOME mapping covers all roles', async () => {
    // Verify each role has a dashboard route
    const { default: router } = await import('@/router/index')
    const roles = ['admin', 'instructor', 'learner', 'finance', 'dataops']
    for (const role of roles) {
      const dashPath = `/${role}/dashboard`
      const route = router.getRoutes().find(r => r.path === dashPath)
      expect(route, `Missing dashboard for ${role}`).toBeTruthy()
    }
  })
})
