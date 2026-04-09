<script setup lang="ts">
import { onMounted } from 'vue'
import { useIngestionStore } from '@/stores/ingestion'
import { useUiStore } from '@/stores/ui'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import { Plus, Zap } from 'lucide-vue-next'

const ingestion = useIngestionStore()
const ui = useUiStore()
const router = useRouter()

onMounted(() => ingestion.fetchSources())

async function handleTest(id: string, event: Event) {
  event.preventDefault()
  try {
    const res = await ingestion.testConnection(id)
    ui.addToast(res.success ? `Connected! ${res.latency_ms}ms` : `Failed: ${res.error}`, res.success ? 'success' : 'error')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
}
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Ingestion Sources</h1>
      <RouterLink to="/dataops/ingestion/new" class="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
        <Plus class="h-4 w-4" /> New Source
      </RouterLink>
    </div>

    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Active</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Last Run</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="ingestion.loading"><td colspan="6" class="py-8 text-center text-muted-foreground">Loading…</td></tr>
          <tr v-for="s in ingestion.sources" :key="s.id" class="border-t border-border hover:bg-muted/30 cursor-pointer" @click="router.push(`/dataops/ingestion/${s.id}`)">
            <td class="px-4 py-3 font-medium text-foreground">{{ s.name }}</td>
            <td class="px-4 py-3 font-mono text-xs text-muted-foreground">{{ s.type }}</td>
            <td class="px-4 py-3">
              <span :class="['text-xs font-medium', s.is_active ? 'text-green-600' : 'text-muted-foreground']">{{ s.is_active ? 'Yes' : 'No' }}</span>
            </td>
            <td class="px-4 py-3 text-xs text-muted-foreground">{{ s.last_run_at?.slice(0, 16) ?? 'Never' }}</td>
            <td class="px-4 py-3"><StatusBadge v-if="s.last_status" :status="s.last_status" /></td>
            <td class="px-4 py-3 text-right">
              <button @click="handleTest(s.id, $event)" class="flex items-center gap-1 px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded hover:bg-accent">
                <Zap class="h-3 w-3" /> Test
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
