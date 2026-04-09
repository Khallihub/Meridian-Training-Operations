import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSearchStore } from '@/stores/search'

vi.mock('@/api/endpoints/search', () => ({
  searchApi: {
    search: vi.fn(),
    getSaved: vi.fn(),
    saveSearch: vi.fn(),
    deleteSearch: vi.fn(),
    export: vi.fn(),
  },
}))

import { searchApi } from '@/api/endpoints/search'

describe('searchStore — correction #2 (50k export guard)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('exportDisabled = false when results ≤ 50k', async () => {
    vi.mocked(searchApi.search).mockResolvedValue({ results: [], total_count: 49999, query_time_ms: 10, facets: undefined })
    const store = useSearchStore()
    await store.runSearch({})
    expect(store.exportDisabled).toBe(false)
  })

  it('exportDisabled = true when results > 50k — correction #2', async () => {
    vi.mocked(searchApi.search).mockResolvedValue({ results: [], total_count: 50001, query_time_ms: 10, facets: undefined })
    const store = useSearchStore()
    await store.runSearch({})
    expect(store.exportDisabled).toBe(true)
  })

  it('saveSearch enforces max 20', async () => {
    const store = useSearchStore()
    // Pre-fill 20 saved searches
    store.savedSearches = Array.from({ length: 20 }, (_, i) => ({ id: `s${i}`, name: `search-${i}`, filters_json: {}, created_at: '' }))
    vi.mocked(searchApi.saveSearch).mockResolvedValue({ id: 'new', name: 'extra', filters_json: {}, created_at: '' })
    await store.saveSearch('extra', {})
    expect(store.savedSearches.length).toBe(20)
  })

  it('facets are populated from search response', async () => {
    vi.mocked(searchApi.search).mockResolvedValue({
      results: [],
      total_count: 5,
      query_time_ms: 3,
      facets: {
        enrollment_status: { confirmed: 3, pending: 2 },
        site: [{ id: 'site1', name: 'Downtown', count: 3 }],
        instructor: [],
      },
    })
    const store = useSearchStore()
    await store.runSearch({}, true)
    expect(store.facets?.enrollment_status.confirmed).toBe(3)
    expect(store.facets?.site[0].name).toBe('Downtown')
  })
})
