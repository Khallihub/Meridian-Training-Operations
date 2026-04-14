import { defineStore } from 'pinia'
import { ref } from 'vue'
import { bookingsApi } from '@/api/endpoints/bookings'

export interface Booking {
  id: string
  session_id: string
  session_title: string
  session_start_time: string
  learner_id: string
  learner_username: string
  status: 'requested' | 'confirmed' | 'rescheduled_out' | 'canceled' | 'completed' | 'no_show'
  policy_fee_flagged: boolean
  cancellation_reason: string | null
  confirmed_at: string | null
  cancelled_at: string | null
  created_at: string
}

export interface BookingHistoryEntry {
  id: string
  from_status: string
  to_status: string
  actor_username: string
  note: string | null
  created_at: string
}

export const useBookingsStore = defineStore('bookings', () => {
  const bookings = ref<Booking[]>([])
  const currentBooking = ref<Booking | null>(null)
  const history = ref<BookingHistoryEntry[]>([])
  const totalCount = ref(0)
  const loading = ref(false)

  async function fetchAll(filters: Record<string, unknown> = {}) {
    loading.value = true
    try {
      const res = await bookingsApi.getAll(filters)
      bookings.value = res.items
      totalCount.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: string) {
    currentBooking.value = await bookingsApi.getOne(id)
    return currentBooking.value
  }

  async function create(sessionId: string) {
    return await bookingsApi.create(sessionId)
  }

  async function confirm(id: string) {
    const updated = await bookingsApi.confirm(id)
    _replaceInList(updated)
    return updated
  }

  async function reschedule(id: string, newSessionId: string) {
    const updated = await bookingsApi.reschedule(id, newSessionId)
    _replaceInList(updated)
    return updated
  }

  async function cancel(id: string, reason?: string) {
    const updated = await bookingsApi.cancel(id, reason)
    _replaceInList(updated)
    return updated
  }

  async function fetchHistory(id: string) {
    history.value = await bookingsApi.getHistory(id)
    return history.value
  }

  function _replaceInList(updated: Booking) {
    const idx = bookings.value.findIndex(b => b.id === updated.id)
    if (idx !== -1) bookings.value[idx] = updated
    if (currentBooking.value?.id === updated.id) currentBooking.value = updated
  }

  return {
    bookings, currentBooking, history, totalCount, loading,
    fetchAll, fetchOne, create, confirm, reschedule, cancel, fetchHistory,
  }
})
