import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useIngestionStore } from '@/stores/ingestion'

vi.mock('@/api/endpoints/ingestion', () => ({
  ingestionApi: {
    getSources: vi.fn(),
    createSource: vi.fn(),
    updateSource: vi.fn(),
    deleteSource: vi.fn(),
    testConnection: vi.fn(),
    triggerRun: vi.fn(),
    getRuns: vi.fn(),
  },
}))

import { ingestionApi } from '@/api/endpoints/ingestion'

const mockSource = {
  id: 'src-1',
  name: 'Kafka Source',
  type: 'kafka' as const,
  collection_frequency_seconds: 300,
  concurrency_cap: 10,
  is_active: true,
  last_run_at: null,
  last_status: null,
}

describe('ingestionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchSources populates sources list', async () => {
    vi.mocked(ingestionApi.getSources).mockResolvedValue([mockSource])
    const store = useIngestionStore()
    await store.fetchSources()
    expect(store.sources).toHaveLength(1)
    expect(store.sources[0].name).toBe('Kafka Source')
    expect(store.loading).toBe(false)
  })

  it('createSource adds to sources', async () => {
    const newSource = { ...mockSource, id: 'src-2', name: 'New Source' }
    vi.mocked(ingestionApi.createSource).mockResolvedValue(newSource)
    const store = useIngestionStore()
    const result = await store.createSource({ name: 'New Source', type: 'kafka' })
    expect(result).toEqual(newSource)
    expect(store.sources).toHaveLength(1)
    expect(store.sources[0].name).toBe('New Source')
  })

  it('updateSource updates in-place', async () => {
    const updated = { ...mockSource, name: 'Updated Source' }
    vi.mocked(ingestionApi.updateSource).mockResolvedValue(updated)
    const store = useIngestionStore()
    store.sources = [mockSource]
    await store.updateSource('src-1', { name: 'Updated Source' })
    expect(store.sources[0].name).toBe('Updated Source')
  })

  it('updateSource refreshes currentSource if matching', async () => {
    const updated = { ...mockSource, name: 'Updated' }
    vi.mocked(ingestionApi.updateSource).mockResolvedValue(updated)
    const store = useIngestionStore()
    store.sources = [mockSource]
    store.currentSource = mockSource
    await store.updateSource('src-1', { name: 'Updated' })
    expect(store.currentSource!.name).toBe('Updated')
  })

  it('deleteSource removes from list', async () => {
    vi.mocked(ingestionApi.deleteSource).mockResolvedValue(undefined)
    const store = useIngestionStore()
    store.sources = [mockSource]
    await store.deleteSource('src-1')
    expect(store.sources).toHaveLength(0)
  })

  it('testConnection calls API', async () => {
    vi.mocked(ingestionApi.testConnection).mockResolvedValue({ success: true, latency_ms: 42 })
    const store = useIngestionStore()
    const result = await store.testConnection('src-1')
    expect(result).toEqual({ success: true, latency_ms: 42 })
  })

  it('triggerRun calls API', async () => {
    const mockRun = { id: 'r-1', source_id: 'src-1', started_at: '2026-04-10T10:00:00Z', finished_at: null, rows_ingested: 0, status: 'running' as const, error_detail: null }
    vi.mocked(ingestionApi.triggerRun).mockResolvedValue(mockRun)
    const store = useIngestionStore()
    const result = await store.triggerRun('src-1')
    expect(result).toEqual(mockRun)
  })

  it('fetchRuns populates runs', async () => {
    const mockRuns = [
      { id: 'r-1', source_id: 'src-1', started_at: '2026-04-10T10:00:00Z', finished_at: '2026-04-10T10:01:00Z', rows_ingested: 100, status: 'succeeded' as const, error_detail: null },
    ]
    vi.mocked(ingestionApi.getRuns).mockResolvedValue(mockRuns)
    const store = useIngestionStore()
    await store.fetchRuns('src-1')
    expect(store.runs).toHaveLength(1)
    expect(store.runs[0].rows_ingested).toBe(100)
  })
})
