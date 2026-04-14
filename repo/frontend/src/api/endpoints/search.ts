import client from '../client'
import type { SearchFilters, SearchResult, SearchFacets, SavedSearch } from '@/stores/search'

export const searchApi = {
  search: async (params: SearchFilters & { include_facets?: boolean }) => {
    const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))
    const res = await client.post('/api/v1/search', clean)
    return res.data as { results: SearchResult[]; total_count: number; query_time_ms: number; facets?: SearchFacets }
  },
  getSaved: async () => {
    const res = await client.get('/api/v1/search/saved')
    return res.data as SavedSearch[]
  },
  saveSearch: async (name: string, filters: SearchFilters) => {
    const res = await client.post('/api/v1/search/saved', { name, filters })
    return res.data as SavedSearch
  },
  deleteSearch: async (id: string) => {
    await client.delete(`/api/v1/search/saved/${id}`)
  },
  createExportJob: async (filters: SearchFilters, format: 'csv' | 'xlsx') => {
    const clean = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '' && v != null))
    const backendFormat = format === 'xlsx' ? 'excel' : format
    const res = await client.post('/api/v1/search/export/jobs', { filters: clean, format: backendFormat })
    return res.data as { id: string; status: string }
  },
  pollExportJob: async (jobId: string) => {
    const res = await client.get(`/api/v1/search/export/jobs/${jobId}`)
    return res.data as { id: string; status: string; error_detail?: string }
  },
  downloadExportJob: async (jobId: string) => {
    const res = await client.get(`/api/v1/search/export/jobs/${jobId}/download`, { responseType: 'blob' })
    return res
  },
}
