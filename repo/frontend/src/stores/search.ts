import { defineStore } from 'pinia'
import { ref } from 'vue'
import { searchApi } from '@/api/endpoints/search'

export interface SearchFilters {
  invoice_number?: string
  learner_phone?: string
  enrollment_status?: string
  date_from?: string
  date_to?: string
  site_id?: string
  instructor_id?: string
  page?: number
  page_size?: number
  cursor?: string
}

export interface SearchResult {
  booking_id: string
  learner_username: string
  learner_phone_masked: string
  session_title: string
  session_date: string
  site_name: string
  instructor_name: string
  status: string
  amount: number | null
  order_id: string | null
  session_id: string
  learner_id: string
}

export interface SearchFacets {
  enrollment_status: Record<string, number>
  site: Array<{ id: string; name: string; count: number }>
  instructor: Array<{ id: string; name: string; count: number }>
}

export interface SavedSearch {
  id: string
  name: string
  filters_json: SearchFilters
  created_at: string
}

export const useSearchStore = defineStore('search', () => {
  const results = ref<SearchResult[]>([])
  const facets = ref<SearchFacets | null>(null)
  const totalCount = ref(0)
  const queryTimeMs = ref(0)
  const savedSearches = ref<SavedSearch[]>([])
  const loading = ref(false)
  const exportDisabled = ref(false)  // true when totalCount > 50000

  async function runSearch(filters: SearchFilters, includeFacets = true) {
    loading.value = true
    try {
      const res = await searchApi.search({ ...filters, include_facets: includeFacets })
      results.value = res.results
      totalCount.value = res.total_count
      queryTimeMs.value = res.query_time_ms
      facets.value = res.facets ?? null
      exportDisabled.value = res.total_count > 50000
    } finally {
      loading.value = false
    }
  }

  async function fetchSaved() {
    savedSearches.value = await searchApi.getSaved()
  }

  async function saveSearch(name: string, filters: SearchFilters) {
    const saved = await searchApi.saveSearch(name, filters)
    savedSearches.value.unshift(saved)
    // Enforce max 20
    if (savedSearches.value.length > 20) savedSearches.value = savedSearches.value.slice(0, 20)
    return saved
  }

  async function deleteSearch(id: string) {
    await searchApi.deleteSearch(id)
    savedSearches.value = savedSearches.value.filter(s => s.id !== id)
  }

  return {
    results, facets, totalCount, queryTimeMs, savedSearches, loading, exportDisabled,
    runSearch, fetchSaved, saveSearch, deleteSearch,
  }
})
