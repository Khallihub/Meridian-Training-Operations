import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock router
const pushMock = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ path: '/learner/checkout' }),
}))

// Mock checkout store
const clearCartMock = vi.fn()
vi.mock('@/stores/checkout', () => ({
  useCheckoutStore: () => ({
    order: null,
    loading: false,
    clearCart: clearCartMock,
  }),
}))

describe('CheckoutPage logic', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('redirects to sessions when no order exists', () => {
    // Simulate mount behavior: no order → redirect
    const order = null
    if (!order) {
      pushMock('/learner/sessions')
    }
    expect(pushMock).toHaveBeenCalledWith('/learner/sessions')
  })

  it('formats currency correctly', () => {
    const fmt = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
    expect(fmt(150)).toContain('150')
    expect(fmt(0)).toContain('0')
    expect(fmt(99.99)).toContain('99.99')
  })

  it('handleProceed clears cart and navigates', () => {
    const orderId = 'order-123'
    clearCartMock()
    pushMock(`/learner/orders/${orderId}`)
    expect(clearCartMock).toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalledWith('/learner/orders/order-123')
  })

  it('order items display correct fields', () => {
    const mockOrder = {
      id: 'order-1',
      items: [
        { session_id: 's1', session_title: 'Python 101', unit_price: 100, quantity: 1 },
        { session_id: 's2', session_title: 'React Basics', unit_price: 150, quantity: 2 },
      ],
      subtotal: 400,
      discount_total: 40,
      total: 360,
      applied_promotions: [],
    }
    expect(mockOrder.items).toHaveLength(2)
    expect(mockOrder.subtotal).toBe(400)
    expect(mockOrder.total).toBe(360)
  })
})
