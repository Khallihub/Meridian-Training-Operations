import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useJobsStore } from '@/stores/jobs'

vi.mock('@/api/endpoints/jobs', () => ({
  jobsApi: {
    getStats: vi.fn(),
    getExecutions: vi.fn(),
    getAlerts: vi.fn(),
    getHealth: vi.fn(),
    triggerJob: vi.fn(),
  },
}))

import { jobsApi } from '@/api/endpoints/jobs'

const mockStats = {
  window_minutes: 60,
  jobs: [
    {
      job_name: 'close-expired-orders',
      total_executions: 10,
      success_count: 9,
      failure_count: 1,
      success_rate_pct: 90.0,
      avg_duration_ms: 150,
      p95_duration_ms: 300,
      last_run_at: '2026-04-10T10:00:00Z',
      last_status: 'success' as const,
    },
  ],
}

describe('jobsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchStats populates stats', async () => {
    vi.mocked(jobsApi.getStats).mockResolvedValue(mockStats)
    const store = useJobsStore()
    await store.fetchStats(60)
    expect(store.stats).toEqual(mockStats)
    expect(store.stats!.jobs).toHaveLength(1)
    expect(store.loading).toBe(false)
  })

  it('fetchExecutions populates executions', async () => {
    const mockExecs = [
      { id: 'e-1', job_name: 'test', started_at: '2026-04-10T10:00:00Z', finished_at: '2026-04-10T10:01:00Z', status: 'success' as const, error_detail: null },
    ]
    vi.mocked(jobsApi.getExecutions).mockResolvedValue(mockExecs)
    const store = useJobsStore()
    await store.fetchExecutions('test')
    expect(store.executions).toHaveLength(1)
    expect(store.executions[0].job_name).toBe('test')
  })

  it('fetchAlerts populates alerts', async () => {
    const mockAlerts = [
      { id: 'a-1', type: 'failure_rate', message: 'High failure', job_name: 'test', created_at: '2026-04-10T10:00:00Z' },
    ]
    vi.mocked(jobsApi.getAlerts).mockResolvedValue(mockAlerts)
    const store = useJobsStore()
    await store.fetchAlerts()
    expect(store.alerts).toHaveLength(1)
  })

  it('fetchHealth sets health state', async () => {
    vi.mocked(jobsApi.getHealth).mockResolvedValue({ status: 'ok', timestamp: '2026-04-10T10:00:00Z' })
    const store = useJobsStore()
    await store.fetchHealth()
    expect(store.health!.status).toBe('ok')
  })

  it('triggerJob sets and clears triggering state', async () => {
    vi.mocked(jobsApi.triggerJob).mockResolvedValue(undefined)
    vi.mocked(jobsApi.getStats).mockResolvedValue(mockStats)
    const store = useJobsStore()
    await store.triggerJob('close-expired-orders')
    expect(store.triggering).toBeNull()
    expect(jobsApi.triggerJob).toHaveBeenCalledWith('close-expired-orders')
  })

  it('loading resets on stats fetch error', async () => {
    vi.mocked(jobsApi.getStats).mockRejectedValue(new Error('fail'))
    const store = useJobsStore()
    await expect(store.fetchStats()).rejects.toThrow()
    expect(store.loading).toBe(false)
  })
})
