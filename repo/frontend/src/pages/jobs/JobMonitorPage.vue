<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import { Play } from 'lucide-vue-next'

const jobs = useJobsStore()
const ui = useUiStore()
const windowMinutes = ref(60)
const expandedJob = ref<string | null>(null)

let pollInterval: ReturnType<typeof setInterval>

onMounted(() => {
  jobs.fetchStats(windowMinutes.value)
  pollInterval = setInterval(() => jobs.fetchStats(windowMinutes.value), 60000)
})

onUnmounted(() => clearInterval(pollInterval))

async function toggleJob(jobName: string) {
  if (expandedJob.value === jobName) {
    expandedJob.value = null
    return
  }
  expandedJob.value = jobName
  await jobs.fetchExecutions(jobName)
}

async function changeWindow(w: number) {
  windowMinutes.value = w
  await jobs.fetchStats(w)
}

async function runNow(jobName: string, event: Event) {
  event.stopPropagation()
  try {
    await jobs.triggerJob(jobName)
    ui.addToast(`Job "${jobName}" queued`, 'success')
  } catch (e: any) {
    ui.addToast(e.message ?? 'Failed to trigger job', 'error')
  }
}

function rateColor(pct: number) {
  if (pct >= 95) return 'text-green-600 dark:text-green-400'
  if (pct >= 80) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
}
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Job Monitor</h1>
      <!-- Window selector -->
      <div class="flex gap-1 border border-border rounded overflow-hidden text-sm">
        <button v-for="w in [60, 360, 1440]" :key="w"
          @click="changeWindow(w)"
          :class="['px-3 py-1.5', windowMinutes === w ? 'bg-primary text-primary-foreground' : 'bg-background text-muted-foreground hover:text-foreground']"
        >{{ w === 60 ? '1h' : w === 360 ? '6h' : '24h' }}</button>
      </div>
    </div>

    <div v-if="jobs.loading" class="text-muted-foreground text-sm">Loading…</div>

    <div v-else-if="jobs.stats" class="flex flex-col gap-2">
      <div class="overflow-x-auto rounded-lg border border-border">
        <table class="w-full text-sm">
          <thead class="bg-muted/50">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground w-8" />
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Job</th>
              <th class="px-4 py-3 text-right font-medium text-muted-foreground">Success Rate</th>
              <th class="px-4 py-3 text-right font-medium text-muted-foreground">Avg ms</th>
              <th class="px-4 py-3 text-right font-medium text-muted-foreground">P95 ms</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Last Run</th>
              <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th class="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            <template v-for="job in jobs.stats.jobs" :key="job.job_name">
              <tr
                class="border-t border-border hover:bg-muted/30 cursor-pointer"
                @click="toggleJob(job.job_name)"
              >
                <td class="px-4 py-3 text-muted-foreground text-xs">{{ expandedJob === job.job_name ? '▼' : '▶' }}</td>
                <td class="px-4 py-3 font-mono text-xs text-foreground">{{ job.job_name }}</td>
                <td :class="['px-4 py-3 text-right font-semibold', rateColor(job.success_rate_pct)]">
                  {{ job.success_rate_pct.toFixed(1) }}%
                </td>
                <td class="px-4 py-3 text-right text-muted-foreground">{{ job.avg_duration_ms }}</td>
                <td class="px-4 py-3 text-right text-muted-foreground">{{ job.p95_duration_ms }}</td>
                <td class="px-4 py-3 text-xs text-muted-foreground">{{ job.last_run_at?.slice(0, 16) ?? '—' }}</td>
                <td class="px-4 py-3">
                  <StatusBadge v-if="job.last_status" :status="job.last_status" />
                  <span v-else class="text-muted-foreground">—</span>
                </td>
                <td class="px-4 py-3">
                  <button
                    @click="runNow(job.job_name, $event)"
                    :disabled="jobs.triggering === job.job_name"
                    class="flex items-center gap-1 px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded hover:bg-accent disabled:opacity-50"
                    title="Run now"
                  >
                    <Play class="h-3 w-3" />
                    {{ jobs.triggering === job.job_name ? '…' : 'Run' }}
                  </button>
                </td>
              </tr>

              <!-- Inline execution history -->
              <tr v-if="expandedJob === job.job_name" class="bg-muted/20">
                <td colspan="8" class="px-6 py-4">
                  <h3 class="text-xs font-medium text-muted-foreground mb-2">Recent Executions</h3>
                  <div class="overflow-x-auto">
                    <table class="w-full text-xs">
                      <thead><tr>
                        <th class="text-left pb-1 text-muted-foreground">Started</th>
                        <th class="text-left pb-1 text-muted-foreground">Finished</th>
                        <th class="text-left pb-1 text-muted-foreground">Status</th>
                        <th class="text-left pb-1 text-muted-foreground">Error</th>
                      </tr></thead>
                      <tbody>
                        <tr v-for="exec in jobs.executions" :key="exec.id" class="border-t border-border/50">
                          <td class="py-1 font-mono">{{ exec.started_at.slice(0, 16) }}</td>
                          <td class="py-1 font-mono">{{ exec.finished_at?.slice(0, 16) ?? '—' }}</td>
                          <td class="py-1"><StatusBadge :status="exec.status" /></td>
                          <td class="py-1 text-red-600 truncate max-w-xs">{{ exec.error_detail ?? '—' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </AppLayout>
</template>
