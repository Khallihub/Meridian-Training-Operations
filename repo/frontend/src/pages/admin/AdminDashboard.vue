<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import { useAuthStore } from '@/stores/auth'
import { format } from 'date-fns'
import AppLayout from '@/layouts/AppLayout.vue'
import StatCard from '@/components/shared/StatCard.vue'
import WeekCalendar from '@/components/calendar/WeekCalendar.vue'
import SessionFlyout from '@/components/sessions/SessionFlyout.vue'
import { adminApi } from '@/api/endpoints/admin'
import type { Session } from '@/stores/sessions'

const sessions = useSessionsStore()
const auth = useAuthStore()
const tz = auth.user?.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone
const recentLogs = ref<any[]>([])
const selectedSession = ref<Session | null>(null)

onMounted(async () => {
  await sessions.fetchWeek(format(new Date(), "yyyy-'W'ww"), tz)
  const res = await adminApi.getAuditLogs({ page_size: 10 })
  recentLogs.value = res.items
})

const today = computed(() => sessions.weekSessions.filter(s => s.start_time.startsWith(format(new Date(), 'yyyy-MM-dd'))))
const liveCount = computed(() => sessions.weekSessions.filter(s => s.status === 'live').length)
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">Dashboard</h1>

    <!-- KPI cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <StatCard label="Sessions Today" :value="today.length" />
      <StatCard label="Live Now" :value="liveCount" />
      <StatCard label="This Week" :value="sessions.weekSessions.length" />
      <StatCard label="Canceled" :value="sessions.weekSessions.filter(s => s.status === 'canceled').length" />
    </div>

    <!-- Calendar -->
    <div class="mb-8">
      <WeekCalendar
        :sessions="sessions.weekSessions"
        :loading="sessions.loading"
        :tz="tz"
        @week-change="(w) => sessions.fetchWeek(w, tz)"
        @session-click="selectedSession = $event"
      />
    </div>

    <!-- Recent audit activity -->
    <div class="bg-card border border-border rounded-lg p-5">
      <h2 class="font-medium text-foreground mb-3">Recent Activity</h2>
      <div class="space-y-2">
        <div v-for="log in recentLogs" :key="log.id" class="flex items-center gap-3 text-sm">
          <span class="text-muted-foreground text-xs w-32 shrink-0">{{ log.created_at?.slice(0, 16) }}</span>
          <span class="font-medium text-foreground">{{ log.actor_username }}</span>
          <span class="text-muted-foreground">{{ log.action }}d</span>
          <span class="font-mono text-xs text-muted-foreground">{{ log.entity_type }}</span>
        </div>
        <div v-if="recentLogs.length === 0" class="text-muted-foreground text-sm">No recent activity.</div>
      </div>
    </div>

    <SessionFlyout :session="selectedSession" :tz="tz" @close="selectedSession = null" @book="() => {}" @live-room="() => {}" @roster="() => {}" />
  </AppLayout>
</template>
