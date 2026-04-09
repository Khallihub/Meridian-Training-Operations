<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useJobsStore } from '@/stores/jobs'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import { ExternalLink } from 'lucide-vue-next'

const jobs = useJobsStore()
let healthInterval: ReturnType<typeof setInterval>

onMounted(() => {
  jobs.fetchHealth()
  jobs.fetchAlerts()
  healthInterval = setInterval(() => { jobs.fetchHealth(); jobs.fetchAlerts() }, 30000)
})
onUnmounted(() => clearInterval(healthInterval))
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Monitoring</h1>
      <a href="http://localhost:3000" target="_blank" rel="noopener" class="flex items-center gap-2 px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">
        <ExternalLink class="h-4 w-4" /> Open Grafana
      </a>
    </div>

    <!-- Health status -->
    <div class="flex items-center gap-3 p-4 rounded-lg bg-card border border-border mb-6">
      <div :class="['h-3 w-3 rounded-full', jobs.health?.status === 'ok' ? 'bg-green-500' : 'bg-red-500 animate-pulse']" />
      <div>
        <p class="text-sm font-medium text-foreground">System Health: {{ jobs.health?.status ?? 'Unknown' }}</p>
        <p v-if="jobs.health?.timestamp" class="text-xs text-muted-foreground">Last checked: {{ jobs.health.timestamp.slice(0, 16) }}</p>
      </div>
    </div>

    <!-- Active alerts -->
    <div class="bg-card border border-border rounded-lg p-5">
      <h2 class="font-medium text-foreground mb-3">Active Alerts ({{ jobs.alerts.length }})</h2>
      <div v-if="jobs.alerts.length === 0" class="text-sm text-muted-foreground">No active alerts. All systems nominal.</div>
      <div v-else class="space-y-3">
        <div
          v-for="alert in jobs.alerts"
          :key="alert.id"
          class="flex items-start gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800"
        >
          <div>
            <p class="text-sm font-medium text-red-800 dark:text-red-200">{{ alert.message }}</p>
            <div class="flex items-center gap-2 mt-1">
              <span v-if="alert.job_name" class="text-xs font-mono text-red-700 dark:text-red-300">{{ alert.job_name }}</span>
              <span class="text-xs text-red-600 dark:text-red-400">{{ alert.created_at.slice(0, 16) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
