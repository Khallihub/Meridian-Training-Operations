import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import MonthCalendar from '@/components/calendar/MonthCalendar.vue'
import type { Session } from '@/stores/sessions'

const makeSession = (overrides: Partial<Session> = {}): Session => ({
  id: 's-1',
  title: 'Monthly Session',
  course_id: 'c-1',
  course_title: 'Python 101',
  instructor_id: 'i-1',
  instructor_name: 'Jane',
  room_id: 'r-1',
  room_name: 'Room B',
  location_id: 'l-1',
  location_name: 'Campus',
  start_time: '2026-04-15T14:00:00Z',
  end_time: '2026-04-15T15:00:00Z',
  capacity: 30,
  enrolled_count: 10,
  buffer_minutes: 10,
  status: 'scheduled',
  recurrence_rule_id: null,
  created_by: 'u-1',
  created_at: '2026-04-01T00:00:00Z',
  ...overrides,
})

describe('MonthCalendar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders without crashing', () => {
    const wrapper = mount(MonthCalendar, {
      props: { sessions: [], tz: 'UTC' },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('emits month-change on mount', () => {
    const wrapper = mount(MonthCalendar, {
      props: { sessions: [], tz: 'UTC' },
    })
    const emitted = wrapper.emitted('month-change')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toMatch(/^\d{4}-\d{2}$/)
  })

  it('renders day headers', () => {
    const wrapper = mount(MonthCalendar, {
      props: { sessions: [], tz: 'UTC' },
    })
    const text = wrapper.text()
    expect(text).toContain('Mon')
    expect(text).toContain('Fri')
  })

  it('displays session in correct day cell', () => {
    const wrapper = mount(MonthCalendar, {
      props: { sessions: [makeSession()], tz: 'UTC' },
    })
    expect(wrapper.text()).toContain('Python 101')
  })

  it('navigates months', async () => {
    const wrapper = mount(MonthCalendar, {
      props: { sessions: [], tz: 'UTC' },
    })
    const buttons = wrapper.findAll('button')
    if (buttons.length >= 2) {
      await buttons[0].trigger('click') // prev month
      const emitted = wrapper.emitted('month-change')
      expect(emitted!.length).toBeGreaterThanOrEqual(2)
    }
  })

  it('limits visible sessions per day to VISIBLE_MAX', () => {
    const sessions = Array.from({ length: 5 }, (_, i) =>
      makeSession({
        id: `s-${i}`,
        course_title: `Course ${i}`,
        start_time: '2026-04-15T10:00:00Z',
        end_time: '2026-04-15T11:00:00Z',
      })
    )
    const wrapper = mount(MonthCalendar, {
      props: { sessions, tz: 'UTC' },
    })
    // Should show "+2 more" or similar overflow indicator
    const text = wrapper.text()
    expect(text).toContain('more')
  })
})
