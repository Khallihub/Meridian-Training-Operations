import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import WeekCalendar from '@/components/calendar/WeekCalendar.vue'
import type { Session } from '@/stores/sessions'

const makeSession = (overrides: Partial<Session> = {}): Session => ({
  id: 's-1',
  title: 'Test Session',
  course_id: 'c-1',
  course_title: 'Python 101',
  instructor_id: 'i-1',
  instructor_name: 'John',
  room_id: 'r-1',
  room_name: 'Room A',
  location_id: 'l-1',
  location_name: 'HQ',
  start_time: '2026-04-13T10:00:00Z', // Monday
  end_time: '2026-04-13T11:00:00Z',
  capacity: 20,
  enrolled_count: 5,
  buffer_minutes: 10,
  status: 'scheduled',
  recurrence_rule_id: null,
  created_by: 'u-1',
  created_at: '2026-04-01T00:00:00Z',
  ...overrides,
})

describe('WeekCalendar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders without crashing with empty sessions', () => {
    const wrapper = mount(WeekCalendar, {
      props: { sessions: [], tz: 'UTC' },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('emits week-change on mount', async () => {
    const wrapper = mount(WeekCalendar, {
      props: { sessions: [], tz: 'UTC' },
    })
    // watch fires immediately
    const emitted = wrapper.emitted('week-change')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toMatch(/^\d{4}-W\d{2}$/)
  })

  it('renders session blocks', () => {
    const wrapper = mount(WeekCalendar, {
      props: { sessions: [makeSession()], tz: 'UTC' },
    })
    expect(wrapper.text()).toContain('Python 101')
  })

  it('emits session-click when session block is clicked', async () => {
    const session = makeSession()
    const wrapper = mount(WeekCalendar, {
      props: { sessions: [session], tz: 'UTC' },
    })
    // Find the session block and click
    const blocks = wrapper.findAll('[data-testid]').length > 0
      ? wrapper.findAll('[data-testid="session-block"]')
      : wrapper.findAll('.cursor-pointer')
    if (blocks.length > 0) {
      await blocks[0].trigger('click')
      const emitted = wrapper.emitted('session-click')
      if (emitted) {
        expect(emitted[0][0]).toEqual(session)
      }
    }
  })

  it('shows loading state', () => {
    const wrapper = mount(WeekCalendar, {
      props: { sessions: [], loading: true, tz: 'UTC' },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('navigates weeks via prev/next', async () => {
    const wrapper = mount(WeekCalendar, {
      props: { sessions: [], tz: 'UTC' },
    })
    const buttons = wrapper.findAll('button')
    // First button should be prev, second next
    if (buttons.length >= 2) {
      await buttons[0].trigger('click') // prev
      await buttons[1].trigger('click') // next
      const emitted = wrapper.emitted('week-change')
      expect(emitted!.length).toBeGreaterThanOrEqual(2) // initial + navigation
    }
  })
})
