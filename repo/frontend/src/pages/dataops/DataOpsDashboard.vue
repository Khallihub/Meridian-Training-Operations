<script setup lang="ts">
import { onMounted } from 'vue'
import { useIngestionStore } from '@/stores/ingestion'
import { useJobsStore } from '@/stores/jobs'
import AppLayout from '@/layouts/AppLayout.vue'
import StatCard from '@/components/shared/StatCard.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const ingestion = useIngestionStore()
const jobs = useJobsStore()

onMounted(async () => {
  await Promise.all([ingestion.fetchSources(), jobs.fetchStats(60)])
})
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">DataOps Dashboard</h1>

    <!-- Job health summary -->
    <div v-if="jobs.stats" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <StatCard label="Tracked Jobs" :value="jobs.stats.jobs.length" />
      <StatCard
        label="Failing"
        :value="jobs.stats.jobs.filter(j => j.success_rate_pct < 95).length"
        :description="`success rate < 95% in last ${jobs.stats.window_minutes}min`"
      />
      <StatCard label="Ingestion Sources" :value="ingestion.sources.length" />
      <StatCard label="Active Sources" :value="ingestion.sources.filter(s => s.is_active).length" />
    </div>

    <!-- Ingestion source cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <RouterLink
        v-for="source in ingestion.sources"
        :key="source.id"
        :to="`/dataops/ingestion/${source.id}`"
        class="block bg-card border border-border rounded-lg p-4 hover:bg-accent transition-colors"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="font-medium text-foreground text-sm">{{ source.name }}</span>
          <StatusBadge :status="source.last_status ?? 'unknown'" />
        </div>
        <div class="flex items-center gap-2 text-xs text-muted-foreground">
          <span class="px-1.5 py-0.5 bg-secondary rounded font-mono">{{ source.type }}</span>
          <span>Last: {{ source.last_run_at?.slice(0, 16) ?? 'never' }}</span>
        </div>
        <div class="mt-2 flex items-center gap-1.5">
          <div :class="['h-2 w-2 rounded-full', source.is_active ? 'bg-green-400' : 'bg-gray-400']" />
          <span class="text-xs text-muted-foreground">{{ source.is_active ? 'Active' : 'Inactive' }}</span>
        </div>
      </RouterLink>
    </div>
  </AppLayout>
</template>
