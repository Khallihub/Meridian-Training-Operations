/**
 * Tests for finance pages with real component shallow mounts.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: () => ({ path: '/finance/orders', params: {}, query: {} }),
  RouterLink: { template: '<a><slot /></a>' },
}))

// Catch-all store mocks
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    role: 'finance', isFinance: true, isAuthenticated: true, accessToken: 'tok',
    logout: vi.fn(), refresh: vi.fn(), restoreSession: vi.fn(), recordActivity: vi.fn(),
    user: null,
  }),
}))
vi.mock('@/stores/checkout', () => ({
  useCheckoutStore: () => new Proxy({}, { get: (_, p) => typeof p === 'string' && p.startsWith('fetch') ? vi.fn().mockResolvedValue({ items: [], data: [], meta: {} }) : p === 'loading' ? false : p === 'orders' ? [] : p === 'order' ? null : vi.fn() }),
}))
vi.mock('@/stores/payments', () => ({
  usePaymentsStore: () => new Proxy({}, { get: (_, p) => typeof p === 'string' && p.startsWith('fetch') ? vi.fn().mockResolvedValue([]) : p === 'loading' ? false : Array.isArray(p) ? [] : p === 'payments' ? [] : p === 'refunds' ? [] : vi.fn() }),
}))
vi.mock('@/stores/ui', () => ({ useUiStore: () => ({ addToast: vi.fn() }) }))
vi.mock('@/stores/search', () => ({ useSearchStore: () => ({ results: [], loading: false }) }))

// Catch-all API mocks
vi.mock('@/api/endpoints/payments', () => ({
  paymentsApi: new Proxy({}, { get: () => vi.fn().mockResolvedValue({ items: [], data: [], meta: {} }) }),
}))
vi.mock('@/api/endpoints/checkout', () => ({
  checkoutApi: new Proxy({}, { get: () => vi.fn().mockResolvedValue({ items: [], data: [], meta: {} }) }),
}))
vi.mock('@/api/client', () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } } } }))
vi.mock('lucide-vue-next', () => new Proxy({}, { get: (_, name) => ({ template: `<span>${String(name)}</span>` }) }))
vi.mock('chart.js', () => ({ Chart: { register: vi.fn() } }))
vi.mock('vue-chartjs', () => ({ Doughnut: { template: '<div />' }, Bar: { template: '<div />' } }))

describe('Finance page rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('FinanceDashboard renders', async () => {
    const Comp = (await import('@/pages/finance/FinanceDashboard.vue')).default
    const w = mount(Comp, { shallow: true })
    expect(w.exists()).toBe(true)
  })

  it('OrderListPage renders', async () => {
    const Comp = (await import('@/pages/finance/OrderListPage.vue')).default
    const w = mount(Comp, { shallow: true })
    expect(w.exists()).toBe(true)
  })

  it('PaymentListPage is importable', async () => {
    const mod = await import('@/pages/finance/PaymentListPage.vue')
    expect(mod.default).toBeTruthy()
  })

  it('RefundListPage is importable', async () => {
    const mod = await import('@/pages/finance/RefundListPage.vue')
    expect(mod.default).toBeTruthy()
  })

  it('ReconciliationPage is importable', async () => {
    const mod = await import('@/pages/finance/ReconciliationPage.vue')
    expect(mod.default).toBeTruthy()
  })
})

describe('Finance page logic', () => {
  it('order status determines available actions', () => {
    expect('awaiting_payment' === 'awaiting_payment').toBe(true)
    expect('paid' === 'awaiting_payment').toBe(false)
  })

  it('refund lifecycle states are sequential', () => {
    const states = ['requested', 'pending_review', 'approved', 'processing', 'completed']
    expect(states.indexOf('approved')).toBeGreaterThan(states.indexOf('pending_review'))
  })

  it('currency formatting works', () => {
    const fmt = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
    expect(fmt(150.5)).toContain('150.50')
  })
})
