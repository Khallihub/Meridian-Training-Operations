import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sessionsApi } from '@/api/endpoints/sessions'

export interface Session {
  id: string
  title: string
  course_id: string
  course_title: string | null
  instructor_id: string
  instructor_name: string | null
  room_id: string
  room_name: string | null
  location_id: string | null
  location_name: string | null
  start_time: string
  end_time: string
  capacity: number
  enrolled_count: number
  buffer_minutes: number
  status: 'draft' | 'scheduled' | 'live' | 'ended' | 'recording_processing' | 'recording_published' | 'closed_no_recording' | 'canceled' | 'archived'
  recurrence_rule_id: string | null
  created_by: string
  created_at: string
}

export const useSessionsStore = defineStore('sessions', () => {
  const weekSessions = ref<Session[]>([])
  const monthlySessions = ref<Session[]>([])
  const currentSession = ref<Session | null>(null)
  const roster = ref<any[]>([])
  const loading = ref(false)

  async function fetchWeek(week: string, tz: string, locationId?: string) {
    loading.value = true
    try {
      weekSessions.value = await sessionsApi.getWeek(week, tz, locationId)
    } finally {
      loading.value = false
    }
  }

  async function fetchMonth(month: string, tz: string) {
    loading.value = true
    try {
      monthlySessions.value = await sessionsApi.getMonth(month, tz)
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: string) {
    loading.value = true
    try {
      currentSession.value = await sessionsApi.getOne(id)
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Partial<Session>) {
    return await sessionsApi.create(payload)
  }

  async function createRecurring(payload: object) {
    return await sessionsApi.createRecurring(payload)
  }

  async function update(id: string, payload: Partial<Session>) {
    const updated = await sessionsApi.update(id, payload)
    if (currentSession.value?.id === id) currentSession.value = updated
    return updated
  }

  async function cancel(id: string) {
    const updated = await sessionsApi.cancel(id)
    if (currentSession.value?.id === id) currentSession.value = updated
    return updated
  }

  async function goLive(id: string) {
    const updated = await sessionsApi.goLive(id)
    if (currentSession.value?.id === id) currentSession.value = updated
    return updated
  }

  async function end(id: string) {
    const updated = await sessionsApi.end(id)
    if (currentSession.value?.id === id) currentSession.value = updated
    return updated
  }

  /** @deprecated use end() */
  async function complete(id: string) {
    return end(id)
  }

  async function fetchRoster(id: string) {
    roster.value = await sessionsApi.getRoster(id)
    return roster.value
  }

  return {
    weekSessions, monthlySessions, currentSession, roster, loading,
    fetchWeek, fetchMonth, fetchOne, create, createRecurring,
    update, cancel, goLive, end, complete, fetchRoster,
  }
})
