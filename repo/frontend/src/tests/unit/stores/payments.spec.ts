import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePaymentsStore } from '@/stores/payments'

vi.mock('@/api/endpoints/payments', () => ({
  paymentsApi: {
    getPayment: vi.fn(),
    submitRefund: vi.fn(),
    approveRefund: vi.fn(),
    completeRefund: vi.fn(),
    getRefunds: vi.fn(),
    triggerExport: vi.fn(),
    getExports: vi.fn(),
  },
}))

import { paymentsApi } from '@/api/endpoints/payments'

describe('paymentsStore — correction #4 (polling)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('pollPayment calls onPaid callback when status becomes completed', async () => {
    let callCount = 0
    vi.mocked(paymentsApi.getPayment).mockImplementation(async () => {
      callCount++
      return {
        id: 'p1', order_id: 'o1', terminal_ref: 'T001', amount: 100,
        status: callCount >= 2 ? 'completed' : 'pending',
        callback_received_at: callCount >= 2 ? new Date().toISOString() : null,
        signature_verified: callCount >= 2,
      }
    })

    const store = usePaymentsStore()
    const onPaid = vi.fn()
    await store.pollPayment('o1', onPaid)

    // First tick — still pending
    await vi.advanceTimersByTimeAsync(3000)
    expect(onPaid).not.toHaveBeenCalled()

    // Second tick — completed
    await vi.advanceTimersByTimeAsync(3000)
    expect(onPaid).toHaveBeenCalledTimes(1)
  })

  it('pollPayment updates currentPayment on each poll', async () => {
    vi.mocked(paymentsApi.getPayment).mockResolvedValue({
      id: 'p1', order_id: 'o1', terminal_ref: null, amount: 50,
      status: 'pending', callback_received_at: null, signature_verified: false,
    })

    const store = usePaymentsStore()
    await store.pollPayment('o1', vi.fn())
    await vi.advanceTimersByTimeAsync(3000)
    expect(store.currentPayment?.status).toBe('pending')
  })
})
