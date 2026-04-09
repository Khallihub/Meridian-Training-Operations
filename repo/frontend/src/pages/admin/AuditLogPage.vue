<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { adminApi, type AuditLog } from '@/api/endpoints/admin'
import AppLayout from '@/layouts/AppLayout.vue'
import DataTable from '@/components/tables/DataTable.vue'
import JSONDiffViewer from '@/components/shared/JSONDiffViewer.vue'
import { formatInTimeZone } from 'date-fns-tz'
import { parseISO } from 'date-fns'
import { Search } from 'lucide-vue-next'

const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
const logs = ref<AuditLog[]>([])
const total = ref(0)
const loading = ref(false)
const expandedId = ref<string | null>(null)

const filters = reactive({
  entity_type: '',
  actor_id: '',
  date_from: '',
  date_to: '',
  page: 1,
  page_size: 25,
})

const columns = [
  { key: 'created_at', label: 'Timestamp', sortable: true },
  { key: 'actor_username', label: 'Actor' },
  { key: 'entity_type', label: 'Entity Type' },
  { key: 'entity_id', label: 'Entity ID' },
  { key: 'action', label: 'Action' },
]

async function fetchLogs() {
  loading.value = true
  try {
    const res = await adminApi.getAuditLogs({ ...filters })
    logs.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(fetchLogs)

function toggleExpand(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

function fmtDate(dt: string) {
  return formatInTimeZone(parseISO(dt), tz, 'MMM d, yyyy HH:mm:ss')
}
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">Audit Logs</h1>

    <!-- Filters -->
    <div class="bg-card border border-border rounded-lg p-4 mb-5 flex flex-wrap gap-3 items-end">
      <div>
        <label class="block text-xs text-muted-foreground mb-1">Entity Type</label>
        <select v-model="filters.entity_type" class="px-2 py-1.5 rounded border border-border bg-background text-sm w-36">
          <option value="">All</option>
          <option value="user">user</option>
          <option value="session">session</option>
          <option value="booking">booking</option>
          <option value="location">location</option>
          <option value="room">room</option>
          <option value="refund">refund</option>
        </select>
      </div>
      <div>
        <label class="block text-xs text-muted-foreground mb-1">Date From</label>
        <input v-model="filters.date_from" type="date" class="px-2 py-1.5 rounded border border-border bg-background text-sm" />
      </div>
      <div>
        <label class="block text-xs text-muted-foreground mb-1">Date To</label>
        <input v-model="filters.date_to" type="date" class="px-2 py-1.5 rounded border border-border bg-background text-sm" />
      </div>
      <button @click="() => { filters.page = 1; fetchLogs() }" class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
        <Search class="h-4 w-4" /> Filter
      </button>
    </div>

    <!-- Custom table with expandable rows for JSON diff — correction #5 -->
    <div class="flex flex-col gap-3">
      <div class="overflow-x-auto rounded-lg border border-border">
        <table class="w-full text-sm">
          <thead class="bg-muted/50">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground w-8" />
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Timestamp</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Actor</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Entity</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Action</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">IP</th>
            </tr>
          </thead>
          <tbody>
            <template v-if="loading">
              <tr><td colspan="6" class="py-12 text-center text-muted-foreground">Loading…</td></tr>
            </template>
            <template v-else>
              <template v-for="log in logs" :key="log.id">
                <tr
                  @click="toggleExpand(log.id)"
                  class="border-t border-border hover:bg-muted/30 cursor-pointer transition-colors"
                >
                  <td class="px-4 py-3 text-muted-foreground">
                    <span class="text-xs">{{ expandedId === log.id ? '▼' : '▶' }}</span>
                  </td>
                  <td class="px-4 py-3 font-mono text-xs text-foreground">{{ fmtDate(log.created_at) }}</td>
                  <td class="px-4 py-3 text-foreground">{{ log.actor_username }}</td>
                  <td class="px-4 py-3 text-foreground">
                    <span class="font-mono text-xs">{{ log.entity_type }}</span>
                    <span class="text-muted-foreground ml-1 font-mono text-xs">{{ log.entity_id.slice(0, 8) }}…</span>
                  </td>
                  <td class="px-4 py-3">
                    <span class="px-2 py-0.5 rounded text-xs font-medium" :class="{
                      'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200': log.action === 'create',
                      'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200': log.action === 'update',
                      'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200': log.action === 'delete',
                    }">{{ log.action }}</span>
                  </td>
                  <td class="px-4 py-3 text-xs text-muted-foreground font-mono">{{ log.ip_address }}</td>
                </tr>

                <!-- Expanded JSON diff row — correction #5 -->
                <tr v-if="expandedId === log.id" class="border-t border-border bg-muted/20">
                  <td colspan="6" class="px-6 py-4">
                    <JSONDiffViewer :old-value="log.old_value" :new-value="log.new_value" />
                  </td>
                </tr>
              </template>
            </template>
          </tbody>
        </table>
      </div>

      <div v-if="total > 0" class="flex justify-between text-xs text-muted-foreground">
        <span>{{ total.toLocaleString() }} total entries</span>
        <div class="flex gap-2">
          <button :disabled="filters.page <= 1" @click="() => { filters.page--; fetchLogs() }" class="px-2 py-1 rounded border border-border hover:bg-accent disabled:opacity-40">←</button>
          <span>Page {{ filters.page }}</span>
          <button :disabled="filters.page * filters.page_size >= total" @click="() => { filters.page++; fetchLogs() }" class="px-2 py-1 rounded border border-border hover:bg-accent disabled:opacity-40">→</button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
