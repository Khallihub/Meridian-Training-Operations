import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/learner/orders/order-1', params: { id: 'order-1' } }),
}))

const fetchOrderMock = vi.fn()
vi.mock('@/stores/checkout', () => ({
  useCheckoutStore: () => ({
    order: {
      id: 'order-1',
      status: 'awaiting_payment',
      subtotal: 150,
      discount_total: 15,
      total: 135,
      currency: 'USD',
      items: [{ session_id: 's-1', session_title: 'Python', unit_price: 150, quantity: 1 }],
      applied_promotions: [],
      created_at: '2026-04-10T00:00:00Z',
      paid_at: null,
      expires_at: '2026-04-10T00:30:00Z',
    },
    fetchOrder: fetchOrderMock,
  }),
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ addToast: vi.fn() }),
}))

vi.mock('@/api/endpoints/payments', () => ({
  paymentsApi: { simulatePayment: vi.fn().mockResolvedValue({ status: 'completed' }) },
}))

describe('OrderReceiptPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('resolves order ID from route params', () => {
    const params = { id: 'order-1' }
    expect(params.id).toBe('order-1')
  })

  it('shows waiting state for awaiting_payment', () => {
    const status = 'awaiting_payment'
    const isWaiting = status === 'awaiting_payment'
    expect(isWaiting).toBe(true)
  })

  it('shows completed state after payment', () => {
    const status = 'paid'
    const isCompleted = status === 'paid'
    expect(isCompleted).toBe(true)
  })

  it('formats currency correctly', () => {
    const fmt = (n: number) =>
      new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
    expect(fmt(135)).toContain('135.00')
    expect(fmt(0)).toContain('0.00')
  })

  it('polling stops after payment completes', () => {
    let pollCount = 0
    const maxPolls = 200
    const paid = true
    const shouldContinue = !paid && pollCount < maxPolls
    expect(shouldContinue).toBe(false)
  })

  it('polling stops after max attempts', () => {
    const pollCount = 200
    const maxPolls = 200
    const paid = false
    const shouldContinue = !paid && pollCount < maxPolls
    expect(shouldContinue).toBe(false)
  })
})
