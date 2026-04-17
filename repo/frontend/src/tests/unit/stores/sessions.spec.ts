import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionsStore } from '@/stores/sessions'

vi.mock('@/api/endpoints/sessions', () => ({
  sessionsApi: {
    getWeek: vi.fn(),
    getMonth: vi.fn(),
    getOne: vi.fn(),
    create: vi.fn(),
    createRecurring: vi.fn(),
    update: vi.fn(),
    cancel: vi.fn(),
    goLive: vi.fn(),
    end: vi.fn(),
    getRoster: vi.fn(),
  },
}))

import { sessionsApi } from '@/api/endpoints/sessions'

const mockSession = {
  id: 's-1',
  title: 'Test Session',
  course_id: 'c-1',
  course_title: 'Python',
  instructor_id: 'i-1',
  instructor_name: 'John',
  room_id: 'r-1',
  room_name: 'Room A',
  location_id: 'l-1',
  location_name: 'HQ',
  start_time: '2026-04-10T10:00:00Z',
  end_time: '2026-04-10T11:00:00Z',
  capacity: 20,
  enrolled_count: 5,
  buffer_minutes: 10,
  status: 'scheduled' as const,
  recurrence_rule_id: null,
  created_by: 'u-1',
  created_at: '2026-04-01T00:00:00Z',
}

describe('sessionsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchWeek populates weekSessions', async () => {
    vi.mocked(sessionsApi.getWeek).mockResolvedValue([mockSession])
    const store = useSessionsStore()
    await store.fetchWeek('2026-W15', 'UTC')
    expect(store.weekSessions).toHaveLength(1)
    expect(store.weekSessions[0].title).toBe('Test Session')
    expect(store.loading).toBe(false)
  })

  it('fetchMonth populates monthlySessions', async () => {
    vi.mocked(sessionsApi.getMonth).mockResolvedValue([mockSession])
    const store = useSessionsStore()
    await store.fetchMonth('2026-04', 'UTC')
    expect(store.monthlySessions).toHaveLength(1)
    expect(store.loading).toBe(false)
  })

  it('fetchOne sets currentSession', async () => {
    vi.mocked(sessionsApi.getOne).mockResolvedValue(mockSession)
    const store = useSessionsStore()
    await store.fetchOne('s-1')
    expect(store.currentSession).toEqual(mockSession)
  })

  it('create calls API and returns result', async () => {
    vi.mocked(sessionsApi.create).mockResolvedValue(mockSession)
    const store = useSessionsStore()
    const result = await store.create({ title: 'New' })
    expect(sessionsApi.create).toHaveBeenCalledWith({ title: 'New' })
    expect(result).toEqual(mockSession)
  })

  it('update refreshes currentSession if matching', async () => {
    const updated = { ...mockSession, title: 'Updated' }
    vi.mocked(sessionsApi.update).mockResolvedValue(updated)
    const store = useSessionsStore()
    store.currentSession = mockSession
    await store.update('s-1', { title: 'Updated' })
    expect(store.currentSession!.title).toBe('Updated')
  })

  it('cancel updates currentSession status', async () => {
    const canceled = { ...mockSession, status: 'canceled' as const }
    vi.mocked(sessionsApi.cancel).mockResolvedValue(canceled)
    const store = useSessionsStore()
    store.currentSession = mockSession
    await store.cancel('s-1')
    expect(store.currentSession!.status).toBe('canceled')
  })

  it('goLive transitions to live', async () => {
    const live = { ...mockSession, status: 'live' as const }
    vi.mocked(sessionsApi.goLive).mockResolvedValue(live)
    const store = useSessionsStore()
    store.currentSession = mockSession
    await store.goLive('s-1')
    expect(store.currentSession!.status).toBe('live')
  })

  it('end transitions to ended', async () => {
    const ended = { ...mockSession, status: 'ended' as const }
    vi.mocked(sessionsApi.end).mockResolvedValue(ended)
    const store = useSessionsStore()
    store.currentSession = { ...mockSession, status: 'live' as const }
    await store.end('s-1')
    expect(store.currentSession!.status).toBe('ended')
  })

  it('fetchRoster populates roster', async () => {
    vi.mocked(sessionsApi.getRoster).mockResolvedValue([{ id: 'u-1', username: 'learner1' }])
    const store = useSessionsStore()
    await store.fetchRoster('s-1')
    expect(store.roster).toHaveLength(1)
  })

  it('loading resets on error', async () => {
    vi.mocked(sessionsApi.getWeek).mockRejectedValue(new Error('fail'))
    const store = useSessionsStore()
    await expect(store.fetchWeek('2026-W15', 'UTC')).rejects.toThrow()
    expect(store.loading).toBe(false)
  })
})
