import client from '../client'
import type { IngestionSource, IngestionRun } from '@/stores/ingestion'

export const ingestionApi = {
  getSources: async () => {
    const res = await client.get('/api/v1/ingestion/sources')
    return res.data as IngestionSource[]
  },
  createSource: async (payload: Partial<IngestionSource>) => {
    const res = await client.post('/api/v1/ingestion/sources', payload)
    return res.data as IngestionSource
  },
  updateSource: async (id: string, payload: Partial<IngestionSource>) => {
    const res = await client.patch(`/api/v1/ingestion/sources/${id}`, payload)
    return res.data as IngestionSource
  },
  deleteSource: async (id: string) => {
    await client.delete(`/api/v1/ingestion/sources/${id}`)
  },
  testConnection: async (id: string) => {
    const res = await client.post(`/api/v1/ingestion/sources/${id}/test-connection`)
    return res.data as { success: boolean; latency_ms: number; error?: string }
  },
  triggerRun: async (id: string) => {
    const res = await client.post(`/api/v1/ingestion/sources/${id}/trigger`)
    return res.data as IngestionRun
  },
  getRuns: async (id: string) => {
    const res = await client.get(`/api/v1/ingestion/sources/${id}/runs`)
    return res.data as IngestionRun[]
  },
  getRun: async (runId: string) => {
    const res = await client.get(`/api/v1/ingestion/runs/${runId}`)
    return res.data as IngestionRun
  },
}
