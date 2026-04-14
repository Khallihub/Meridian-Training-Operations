import client from '../client'
import type { Session } from '@/stores/sessions'

export const sessionsApi = {
  getWeek: async (week: string, tz: string, locationId?: string) => {
    const res = await client.get('/api/v1/sessions', { params: { week, tz, location_id: locationId } })
    return res.data as Session[]
  },
  getMonth: async (month: string, tz: string) => {
    const res = await client.get('/api/v1/sessions/monthly', { params: { month, tz } })
    return res.data as Session[]
  },
  getOne: async (id: string) => {
    const res = await client.get(`/api/v1/sessions/${id}`)
    return res.data as Session
  },
  create: async (payload: Partial<Session>) => {
    const res = await client.post('/api/v1/sessions', payload)
    return res.data as Session
  },
  createRecurring: async (payload: object) => {
    const res = await client.post('/api/v1/sessions/recurring', payload)
    return res.data
  },
  update: async (id: string, payload: Partial<Session>) => {
    const res = await client.patch(`/api/v1/sessions/${id}`, payload)
    return res.data as Session
  },
  cancel: async (id: string) => {
    const res = await client.patch(`/api/v1/sessions/${id}/cancel`)
    return res.data as Session
  },
  goLive: async (id: string) => {
    const res = await client.post(`/api/v1/sessions/${id}/go-live`)
    return res.data as Session
  },
  end: async (id: string) => {
    const res = await client.post(`/api/v1/sessions/${id}/end`)
    return res.data as Session
  },
  /** @deprecated use end() */
  complete: async (id: string) => {
    const res = await client.post(`/api/v1/sessions/${id}/end`)
    return res.data as Session
  },
  getRoster: async (id: string) => {
    const res = await client.get(`/api/v1/sessions/${id}/roster`)
    return res.data
  },
  getRecordings: async (sessionId: string) => {
    const res = await client.get(`/api/v1/sessions/${sessionId}/recordings`)
    return res.data as Array<{ id: string; mime_type: string; file_size_bytes: number | null; duration_seconds: number | null; created_at: string }>
  },
  recordingStreamUrl: (sessionId: string, recordingId: string, token: string) => {
    return `/api/v1/sessions/${sessionId}/recordings/${recordingId}/stream?token=${encodeURIComponent(token)}`
  },
  setReplayAccessRule: async (id: string, rule: object) => {
    const res = await client.post(`/api/v1/sessions/${id}/replay/access-rule`, rule)
    return res.data
  },
  checkin: async (sessionId: string, learnerId?: string) => {
    const res = await client.post(`/api/v1/sessions/${sessionId}/attendance/checkin`, learnerId ? { learner_id: learnerId } : {})
    return res.data
  },
  checkout: async (sessionId: string, learnerId?: string) => {
    const res = await client.post(`/api/v1/sessions/${sessionId}/attendance/checkout`, learnerId ? { learner_id: learnerId } : {})
    return res.data
  },
  getAttendanceStats: async (sessionId: string) => {
    const res = await client.get(`/api/v1/sessions/${sessionId}/attendance/stats`)
    return res.data
  },
  initiateRecordingUpload: async (sessionId: string) => {
    const res = await client.post(`/api/v1/sessions/${sessionId}/replay/upload`)
    return res.data as { presigned_url: string; object_key: string; bucket: string }
  },
  confirmRecordingUpload: async (sessionId: string, fileSizeBytes: number, durationSeconds: number) => {
    await client.patch(`/api/v1/sessions/${sessionId}/replay/recording`, null, {
      params: { file_size_bytes: fileSizeBytes, duration_seconds: durationSeconds },
    })
  },
  uploadRecordingDirect: async (sessionId: string, blob: Blob, mimeType: string, durationSeconds: number) => {
    const form = new FormData()
    form.append('file', blob, 'recording.webm')
    form.append('duration_seconds', String(durationSeconds))
    // Do NOT set Content-Type manually — browser must set it with the multipart boundary
    const res = await client.post(`/api/v1/sessions/${sessionId}/replay/recording/data`, form)
    return res.data
  },
}
