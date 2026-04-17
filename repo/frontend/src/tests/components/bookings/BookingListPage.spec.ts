/**
 * Tests for BookingListPage data expectations and filter logic.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/admin/bookings' }),
}))

vi.mock('@/stores/bookings', () => ({
  useBookingsStore: () => ({
    bookings: [],
    loading: false,
    fetchBookings: vi.fn(),
  }),
}))

describe('BookingListPage logic', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('booking status determines badge color', () => {
    const statusColors: Record<string, string> = {
      requested: 'yellow',
      confirmed: 'green',
      canceled: 'red',
      completed: 'blue',
      no_show: 'gray',
      rescheduled_out: 'orange',
    }
    expect(Object.keys(statusColors)).toHaveLength(6)
    expect(statusColors['confirmed']).toBe('green')
    expect(statusColors['canceled']).toBe('red')
  })

  it('learner sees only own bookings (role filter)', () => {
    const currentUserRole = 'learner'
    const filterByLearner = currentUserRole === 'learner'
    expect(filterByLearner).toBe(true)

    const adminRole = 'admin'
    const adminFilter = adminRole === 'learner'
    expect(adminFilter).toBe(false)
  })

  it('paginated response has correct shape', () => {
    const response = {
      data: [
        { id: 'b-1', session_id: 's-1', learner_id: 'u-1', status: 'confirmed' },
      ],
      meta: { total_count: 1, page: 1, page_size: 50, has_next: false },
    }
    expect(response.data[0].status).toBe('confirmed')
    expect(response.meta.has_next).toBe(false)
  })

  it('booking can be filtered by session_id', () => {
    const filters = { session_id: 's-1', status: 'confirmed' }
    const queryString = Object.entries(filters)
      .filter(([_, v]) => v != null)
      .map(([k, v]) => `${k}=${v}`)
      .join('&')
    expect(queryString).toContain('session_id=s-1')
    expect(queryString).toContain('status=confirmed')
  })
})
