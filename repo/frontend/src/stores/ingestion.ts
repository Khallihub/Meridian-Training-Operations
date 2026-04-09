import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ingestionApi } from '@/api/endpoints/ingestion'

export interface IngestionSource {
  id: string
  name: string
  type: 'kafka' | 'logstash' | 'batch_file' | 'cdc_mysql' | 'cdc_pg'
  collection_frequency_seconds: number
  concurrency_cap: number
  is_active: boolean
  last_run_at: string | null
  last_status: 'success' | 'failure' | 'running' | null
}

export interface IngestionRun {
  id: string
  source_id: string
  started_at: string
  finished_at: string | null
  rows_ingested: number
  status: 'running' | 'success' | 'failure'
  error_detail: string | null
}

export const useIngestionStore = defineStore('ingestion', () => {
  const sources = ref<IngestionSource[]>([])
  const currentSource = ref<IngestionSource | null>(null)
  const runs = ref<IngestionRun[]>([])
  const loading = ref(false)

  async function fetchSources() {
    loading.value = true
    try { sources.value = await ingestionApi.getSources() }
    finally { loading.value = false }
  }

  async function createSource(payload: Partial<IngestionSource>) {
    const s = await ingestionApi.createSource(payload)
    sources.value.unshift(s)
    return s
  }

  async function updateSource(id: string, payload: Partial<IngestionSource>) {
    const s = await ingestionApi.updateSource(id, payload)
    const idx = sources.value.findIndex(x => x.id === id)
    if (idx !== -1) sources.value[idx] = s
    if (currentSource.value?.id === id) currentSource.value = s
    return s
  }

  async function deleteSource(id: string) {
    await ingestionApi.deleteSource(id)
    sources.value = sources.value.filter(s => s.id !== id)
  }

  async function testConnection(id: string) {
    return await ingestionApi.testConnection(id)
  }

  async function triggerRun(id: string) {
    return await ingestionApi.triggerRun(id)
  }

  async function fetchRuns(id: string) {
    runs.value = await ingestionApi.getRuns(id)
  }

  return {
    sources, currentSource, runs, loading,
    fetchSources, createSource, updateSource, deleteSource,
    testConnection, triggerRun, fetchRuns,
  }
})
