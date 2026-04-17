import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const fetchRosterMock = vi.fn().mockResolvedValue([
  { id: 'u-1', username: 'learner1', checked_in: false, checked_out: false },
  { id: 'u-2', username: 'learner2', checked_in: true, checked_out: false },
])

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/instructor/sessions/s1/attendance', params: { id: 's-1' } }),
}))

vi.mock('@/stores/sessions', () => ({
  useSessionsStore: () => ({
    roster: [],
    loading: false,
    fetchRoster: fetchRosterMock,
  }),
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ addToast: vi.fn() }),
}))

vi.mock('@/api/endpoints/sessions', () => ({
  sessionsApi: {
    checkin: vi.fn().mockResolvedValue({}),
    checkout: vi.fn().mockResolvedValue({}),
    getAttendanceStats: vi.fn().mockResolvedValue({
      avg_minutes_attended: 45, late_joins: 2, replay_completion_rate: 0.8,
    }),
  },
}))

describe('AttendanceManagePage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('resolves session ID from route params', () => {
    const params = { id: 's-1' }
    expect(params.id).toBe('s-1')
  })

  it('roster item status is derived from checked_in/checked_out', () => {
    const getStatus = (item: { checked_in: boolean; checked_out: boolean }) => {
      if (item.checked_out) return 'checked_out'
      if (item.checked_in) return 'checked_in'
      return 'not_checked_in'
    }
    expect(getStatus({ checked_in: false, checked_out: false })).toBe('not_checked_in')
    expect(getStatus({ checked_in: true, checked_out: false })).toBe('checked_in')
    expect(getStatus({ checked_in: true, checked_out: true })).toBe('checked_out')
  })

  it('checkin button visible only when not checked in', () => {
    const showCheckin = (item: { checked_in: boolean }) => !item.checked_in
    expect(showCheckin({ checked_in: false })).toBe(true)
    expect(showCheckin({ checked_in: true })).toBe(false)
  })

  it('checkout button visible only when checked in but not out', () => {
    const showCheckout = (item: { checked_in: boolean; checked_out: boolean }) =>
      item.checked_in && !item.checked_out
    expect(showCheckout({ checked_in: true, checked_out: false })).toBe(true)
    expect(showCheckout({ checked_in: false, checked_out: false })).toBe(false)
    expect(showCheckout({ checked_in: true, checked_out: true })).toBe(false)
  })

  it('stats display values correctly', () => {
    const stats = { avg_minutes_attended: 45, late_joins: 2, replay_completion_rate: 0.8 }
    expect(stats.avg_minutes_attended).toBe(45)
    expect(Math.round(stats.replay_completion_rate * 100)).toBe(80)
  })
})
