import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCheckoutStore } from '@/stores/checkout'

vi.mock('@/api/endpoints/checkout', () => ({
  checkoutApi: {
    createCart: vi.fn(),
    getOrder: vi.fn(),
    getOrders: vi.fn(),
    cancelOrder: vi.fn(),
  },
}))

import { checkoutApi } from '@/api/endpoints/checkout'

const mockOrder = {
  id: 'order-1',
  learner_id: 'learner-1',
  status: 'awaiting_payment' as const,
  subtotal: 100,
  discount_total: 15,
  total: 85,
  currency: 'USD',
  applied_promotions: [],
  items: [{ session_id: 's1', session_title: 'Test Session', unit_price: 100, quantity: 1 }],
  created_at: '2026-04-08T00:00:00Z',
  paid_at: null,
  expires_at: '2026-04-08T00:30:00Z',
}

const mockCancelledOrder = { ...mockOrder, status: 'canceled' as const }

describe('checkoutStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('createCart sets order state', async () => {
    vi.mocked(checkoutApi.createCart).mockResolvedValue(mockOrder)

    const store = useCheckoutStore()
    const result = await store.createCart([{ session_id: 's1', quantity: 1 }])

    expect(checkoutApi.createCart).toHaveBeenCalledWith([{ session_id: 's1', quantity: 1 }])
    expect(result).toEqual(mockOrder)
    expect(store.order).toEqual(mockOrder)
  })

  it('createCart sets loading to false after completion', async () => {
    vi.mocked(checkoutApi.createCart).mockResolvedValue(mockOrder)

    const store = useCheckoutStore()
    await store.createCart([])

    expect(store.loading).toBe(false)
  })

  it('fetchOrder sets order state', async () => {
    vi.mocked(checkoutApi.getOrder).mockResolvedValue(mockOrder)

    const store = useCheckoutStore()
    const result = await store.fetchOrder('order-1')

    expect(checkoutApi.getOrder).toHaveBeenCalledWith('order-1')
    expect(result).toEqual(mockOrder)
    expect(store.order).toEqual(mockOrder)
  })

  it('cancelOrder updates order to cancelled state', async () => {
    vi.mocked(checkoutApi.cancelOrder).mockResolvedValue(mockCancelledOrder)

    const store = useCheckoutStore()
    store.order = mockOrder
    const result = await store.cancelOrder('order-1')

    expect(checkoutApi.cancelOrder).toHaveBeenCalledWith('order-1')
    expect(result!.status).toBe('canceled')
    expect(store.order!.status).toBe('canceled')
  })

  it('clearCart resets order to null', async () => {
    const store = useCheckoutStore()
    store.order = mockOrder
    store.clearCart()

    expect(store.order).toBeNull()
  })
})
