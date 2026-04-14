import { ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import type { SearchFilters } from '@/stores/search'

const POLL_INTERVAL_MS = 2000
const POLL_TIMEOUT_MS = 120_000

export function useExport() {
  const ui = useUiStore()
  const auth = useAuthStore()
  const exporting = ref(false)

  async function exportSearch(filters: SearchFilters, format: 'csv' | 'xlsx') {
    exporting.value = true
    ui.addToast(`Queuing ${format.toUpperCase()} export…`, 'info')
    try {
      const cleanFilters = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== '' && v != null)
      )
      const backendFormat = format === 'xlsx' ? 'excel' : format

      // Step 1: create async export job
      const createRes = await fetch('/api/v1/search/export/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${auth.accessToken}`,
        },
        body: JSON.stringify({ filters: cleanFilters, format: backendFormat }),
      })
      if (!createRes.ok) {
        const body = await createRes.json().catch(() => ({}))
        throw new Error(body.detail ?? `Export request failed: ${createRes.statusText}`)
      }
      const job = await createRes.json()
      const jobId: string = job.id

      ui.addToast('Export queued — processing…', 'info')

      // Step 2: poll until completed or failed
      const deadline = Date.now() + POLL_TIMEOUT_MS
      let status = job.status as string
      while (status === 'queued' || status === 'running') {
        if (Date.now() > deadline) throw new Error('Export timed out. Please try again.')
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS))
        const pollRes = await fetch(`/api/v1/search/export/jobs/${jobId}`, {
          headers: { 'Authorization': `Bearer ${auth.accessToken}` },
        })
        if (!pollRes.ok) throw new Error(`Export polling failed: ${pollRes.statusText}`)
        const pollData = await pollRes.json()
        status = pollData.status
        if (status === 'failed') throw new Error(pollData.error_detail ?? 'Export job failed on server.')
      }

      // Step 3: download the completed file
      const dlRes = await fetch(`/api/v1/search/export/jobs/${jobId}/download`, {
        headers: { 'Authorization': `Bearer ${auth.accessToken}` },
      })
      if (!dlRes.ok) throw new Error(`Download failed: ${dlRes.statusText}`)

      const blob = await dlRes.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `export_${new Date().toISOString().split('T')[0]}.${format === 'xlsx' ? 'xlsx' : 'csv'}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      ui.addToast('Export downloaded', 'success')
    } catch (e: any) {
      ui.addToast(e.message ?? 'Export failed', 'error')
    } finally {
      exporting.value = false
    }
  }

  return { exporting, exportSearch }
}
