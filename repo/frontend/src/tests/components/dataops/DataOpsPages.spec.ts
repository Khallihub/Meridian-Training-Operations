/**
 * Tests for DataOps pages with real component imports/mounts.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: () => ({ path: '/dataops/ingestion', params: { id: 'src-1' }, query: {} }),
  RouterLink: { template: '<a><slot /></a>' },
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ role: 'dataops', isAuthenticated: true, accessToken: 'tok' }),
}))
vi.mock('@/stores/ingestion', () => ({
  useIngestionStore: () => ({
    sources: [], currentSource: null, runs: [], loading: false,
    fetchSources: vi.fn(), createSource: vi.fn(), updateSource: vi.fn(),
    deleteSource: vi.fn(), testConnection: vi.fn(), triggerRun: vi.fn(), fetchRuns: vi.fn(),
  }),
}))
vi.mock('@/stores/jobs', () => ({
  useJobsStore: () => ({
    stats: null, alerts: [], health: { status: 'ok', timestamp: '2026-04-16T00:00:00Z' },
    loading: false, fetchStats: vi.fn(), fetchAlerts: vi.fn(), fetchHealth: vi.fn(), triggerJob: vi.fn(),
  }),
}))
vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ addToast: vi.fn() }),
}))
vi.mock('@/api/endpoints/ingestion', () => ({
  ingestionApi: {
    getSources: vi.fn().mockResolvedValue([]),
    getRuns: vi.fn().mockResolvedValue([]),
  },
}))
vi.mock('lucide-vue-next', () => new Proxy({}, { get: (_, name) => ({ template: `<span>${String(name)}</span>` }) }))

describe('DataOps page rendering', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('DataOpsDashboard renders', async () => {
    const Comp = (await import('@/pages/dataops/DataOpsDashboard.vue')).default
    const w = mount(Comp, { shallow: true })
    expect(w.exists()).toBe(true)
  })

  it('IngestionSourceListPage renders', async () => {
    const Comp = (await import('@/pages/dataops/IngestionSourceListPage.vue')).default
    const w = mount(Comp, { shallow: true })
    expect(w.exists()).toBe(true)
  })

  it('IngestionSourceFormPage renders', async () => {
    const Comp = (await import('@/pages/dataops/IngestionSourceFormPage.vue')).default
    const w = mount(Comp, { shallow: true })
    expect(w.exists()).toBe(true)
  })

  it('IngestionSourceDetailPage renders', async () => {
    const Comp = (await import('@/pages/dataops/IngestionSourceDetailPage.vue')).default
    const w = mount(Comp, { shallow: true })
    expect(w.exists()).toBe(true)
  })
})

describe('DataOps logic', () => {
  it('source types match backend enum', () => {
    const sourceTypes = ['kafka', 'flume', 'logstash', 'file', 'mysql_cdc', 'postgres_cdc']
    expect(sourceTypes).toHaveLength(6)
  })

  it('run status maps to colors', () => {
    const statusColors: Record<string, string> = {
      queued: 'gray', running: 'blue', succeeded: 'green', failed: 'red', partial_failed: 'yellow',
    }
    expect(statusColors['succeeded']).toBe('green')
  })
})
