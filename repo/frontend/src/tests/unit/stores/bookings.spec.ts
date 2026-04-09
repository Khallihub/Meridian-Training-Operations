import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBookingsStore } from '@/stores/bookings'

vi.mock('@/api/endpoints/bookings', () => ({
  bookingsApi: {
    getAll: vi.fn(),
    getOne: vi.fn(),
    create: vi.fn(),
    confirm: vi.fn(),
    reschedule: vi.fn(),
    cancel: vi.fn(),
    getHistory: vi.fn(),
  },
}))

import { bookingsApi } from '@/api/endpoints/bookings'

describe('bookingsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('cancel within 24h sets policy_fee_flagged', async () => {
    vi.mocked(bookingsApi.cancel).mockResolvedValue({
      id: 'b1',
      session_id: 's1',
      session_title: 'Workshop',
      session_start_time: new Date(Date.now() + 3600 * 1000).toISOString(), // 1h from now
      learner_id: 'l1',
      learner_username: 'alice',
      status: 'cancelled',
      policy_fee_flagged: true,  // within 24h
      cancellation_reason: 'changed plans',
      confirmed_at: null,
      cancelled_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
    })

    const store = useBookingsStore()
    const booking = await store.cancel('b1', 'changed plans')
    expect(booking.policy_fee_flagged).toBe(true)
  })

  it('reschedule propagates API error for within-2h window', async () => {
    const err = Object.assign(new Error('Cannot reschedule less than 2 hours before session'), { statusCode: 422 })
    vi.mocked(bookingsApi.reschedule).mockRejectedValue(err)

    const store = useBookingsStore()
    await expect(store.reschedule('b1', 's2')).rejects.toThrow('2 hours')
  })

  it('fetchAll populates bookings and totalCount', async () => {
    vi.mocked(bookingsApi.getAll).mockResolvedValue({
      items: [{ id: 'b1', session_id: 's1', session_title: 'Test', session_start_time: '', learner_id: 'l1', learner_username: 'a', status: 'confirmed', policy_fee_flagged: false, cancellation_reason: null, confirmed_at: null, cancelled_at: null, created_at: '' }],
      total: 1,
    })
    const store = useBookingsStore()
    await store.fetchAll({})
    expect(store.bookings).toHaveLength(1)
    expect(store.totalCount).toBe(1)
  })
})
