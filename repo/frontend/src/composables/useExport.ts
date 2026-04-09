import { ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import type { SearchFilters } from '@/stores/search'

export function useExport() {
  const ui = useUiStore()
  const auth = useAuthStore()
  const exporting = ref(false)

  async function exportSearch(filters: SearchFilters, format: 'csv' | 'xlsx') {
    exporting.value = true
    ui.addToast(`Preparing ${format.toUpperCase()} export…`, 'info')
    try {
      const cleanFilters = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== '' && v != null)
      )
      const backendFormat = format === 'xlsx' ? 'excel' : format
      const res = await fetch('/api/search/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${auth.accessToken}`,
        },
        body: JSON.stringify({ filters: cleanFilters, format: backendFormat }),
      })

      if (!res.ok) {
        if (res.status === 400) {
          const body = await res.json()
          throw new Error(body.detail ?? 'Export limit exceeded (max 50,000 rows)')
        }
        throw new Error(`Export failed: ${res.statusText}`)
      }

      // Stream blob download
      const blob = await res.blob()
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
