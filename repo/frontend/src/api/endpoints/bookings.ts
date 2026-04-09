import client from '../client'
import type { Booking, BookingHistoryEntry } from '@/stores/bookings'

export const bookingsApi = {
  getAll: async (params: Record<string, unknown>) => {
    const res = await client.get('/api/bookings', { params })
    return { items: res.data.items as Booking[], total: res.data.meta.total_count as number }
  },
  getOne: async (id: string) => {
    const res = await client.get(`/api/bookings/${id}`)
    return res.data as Booking
  },
  create: async (sessionId: string) => {
    const res = await client.post('/api/bookings', { session_id: sessionId })
    return res.data as Booking
  },
  confirm: async (id: string) => {
    const res = await client.patch(`/api/bookings/${id}/confirm`)
    return res.data as Booking
  },
  reschedule: async (id: string, newSessionId: string) => {
    const res = await client.post(`/api/bookings/${id}/reschedule`, { new_session_id: newSessionId })
    return res.data as Booking
  },
  cancel: async (id: string, reason?: string) => {
    const res = await client.post(`/api/bookings/${id}/cancel`, { reason })
    return res.data as Booking
  },
  getHistory: async (id: string) => {
    const res = await client.get(`/api/bookings/${id}/history`)
    return res.data as BookingHistoryEntry[]
  },
}
