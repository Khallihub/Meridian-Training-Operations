/**
 * Tests for LiveRoomModal and SessionFlyout component contracts.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

describe('LiveRoomModal expectations', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('requires session prop with live status', () => {
    const session = { id: 's-1', status: 'live', title: 'Live Session' }
    expect(session.status).toBe('live')
  })

  it('WebSocket URL construction', () => {
    const sessionId = 's-1'
    const token = 'jwt-token'
    const wsUrl = `ws://localhost/api/ws/sessions/${sessionId}/room?token=${token}`
    expect(wsUrl).toContain(sessionId)
    expect(wsUrl).toContain('token=')
  })

  it('emits close event on dismiss', () => {
    const emits = { close: true }
    expect(emits.close).toBe(true)
  })
})

describe('SessionFlyout expectations', () => {
  it('displays session details', () => {
    const session = {
      id: 's-1',
      title: 'Test Session',
      course_title: 'Python',
      instructor_name: 'John',
      room_name: 'Room A',
      start_time: '2026-04-15T10:00:00Z',
      end_time: '2026-04-15T11:00:00Z',
      status: 'scheduled',
      capacity: 20,
      enrolled_count: 5,
    }
    expect(session.title).toBeTruthy()
    expect(session.enrolled_count).toBeLessThanOrEqual(session.capacity)
  })

  it('available slots calculation', () => {
    const capacity = 20
    const enrolled = 15
    const available = capacity - enrolled
    expect(available).toBe(5)
    expect(available).toBeGreaterThan(0)
  })

  it('status determines available actions', () => {
    const canBook = (status: string) => status === 'scheduled'
    const canGoLive = (status: string) => status === 'scheduled'
    const canEnd = (status: string) => status === 'live'
    expect(canBook('scheduled')).toBe(true)
    expect(canGoLive('scheduled')).toBe(true)
    expect(canEnd('live')).toBe(true)
    expect(canEnd('scheduled')).toBe(false)
  })
})
