import client from '../client'
import type { JobStat, JobExecution, Alert } from '@/stores/jobs'

export const jobsApi = {
  getStats: async (windowMinutes = 60) => {
    const res = await client.get('/api/jobs/stats/aggregate', { params: { window_minutes: windowMinutes } })
    return res.data as { window_minutes: number; jobs: JobStat[] }
  },
  getExecutions: async (jobName: string) => {
    const res = await client.get(`/api/jobs/${jobName}/executions`)
    return res.data as JobExecution[]
  },
  getAlerts: async () => {
    const res = await client.get('/api/monitoring/alerts')
    return res.data as Alert[]
  },
  getHealth: async () => {
    const res = await client.get('/api/monitoring/health')
    return res.data as { status: string; timestamp: string }
  },
  triggerJob: async (jobName: string) => {
    const res = await client.post(`/api/jobs/${encodeURIComponent(jobName)}/trigger`)
    return res.data as { queued: string }
  },
}
