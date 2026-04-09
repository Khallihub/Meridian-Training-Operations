<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useIngestionStore } from '@/stores/ingestion'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import { Play, Zap } from 'lucide-vue-next'

const route = useRoute()
const ingestion = useIngestionStore()
const ui = useUiStore()
const id = route.params.id as string

onMounted(async () => {
  await Promise.all([
    ingestion.fetchSources(),
    ingestion.fetchRuns(id),
  ])
  ingestion.currentSource = ingestion.sources.find(s => s.id === id) ?? null
})

async function triggerRun() {
  try {
    await ingestion.triggerRun(id)
    ui.addToast('Run triggered', 'success')
    setTimeout(() => ingestion.fetchRuns(id), 2000)
  } catch (e: any) { ui.addToast(e.message, 'error') }
}

async function testConn() {
  try {
    const res = await ingestion.testConnection(id)
    ui.addToast(res.success ? `Connected! ${res.latency_ms}ms` : `Failed: ${res.error}`, res.success ? 'success' : 'error')
  } catch (e: any) { ui.addToast(e.message, 'error') }
}
</script>

<template>
  <AppLayout>
    <div v-if="ingestion.currentSource">
      <div class="flex items-start justify-between mb-6">
        <div>
          <h1 class="text-xl font-semibold text-foreground">{{ ingestion.currentSource.name }}</h1>
          <div class="flex items-center gap-2 mt-1">
            <span class="font-mono text-xs bg-secondary px-2 py-0.5 rounded">{{ ingestion.currentSource.type }}</span>
            <StatusBadge v-if="ingestion.currentSource.last_status" :status="ingestion.currentSource.last_status" />
          </div>
        </div>
        <div class="flex gap-2">
          <button @click="testConn" class="flex items-center gap-2 px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">
            <Zap class="h-4 w-4" /> Test Connection
          </button>
          <button @click="triggerRun" class="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
            <Play class="h-4 w-4" /> Trigger Run
          </button>
        </div>
      </div>

      <!-- Config summary -->
      <div class="bg-card border border-border rounded-lg p-5 mb-6 grid grid-cols-2 gap-4 text-sm">
        <div><p class="text-muted-foreground">Frequency</p><p>{{ ingestion.currentSource.collection_frequency_seconds }}s</p></div>
        <div><p class="text-muted-foreground">Concurrency</p><p>{{ ingestion.currentSource.concurrency_cap }}</p></div>
        <div><p class="text-muted-foreground">Active</p><p>{{ ingestion.currentSource.is_active ? 'Yes' : 'No' }}</p></div>
        <div><p class="text-muted-foreground">Last Run</p><p>{{ ingestion.currentSource.last_run_at?.slice(0, 16) ?? 'Never' }}</p></div>
      </div>

      <!-- Run history -->
      <h2 class="font-medium text-foreground mb-3">Run History</h2>
      <div class="overflow-x-auto rounded-lg border border-border">
        <table class="w-full text-sm">
          <thead class="bg-muted/50">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Started</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Finished</th>
              <th class="px-4 py-3 text-right font-medium text-muted-foreground">Rows</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Error</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in ingestion.runs" :key="run.id" class="border-t border-border hover:bg-muted/30">
              <td class="px-4 py-3 text-xs font-mono">{{ run.started_at.slice(0, 16) }}</td>
              <td class="px-4 py-3 text-xs font-mono text-muted-foreground">{{ run.finished_at?.slice(0, 16) ?? '—' }}</td>
              <td class="px-4 py-3 text-right">{{ run.rows_ingested.toLocaleString() }}</td>
              <td class="px-4 py-3"><StatusBadge :status="run.status" /></td>
              <td class="px-4 py-3 text-xs text-red-600 dark:text-red-400 max-w-xs truncate">{{ run.error_detail ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="text-muted-foreground py-16 text-center">Loading source…</div>
  </AppLayout>
</template>
