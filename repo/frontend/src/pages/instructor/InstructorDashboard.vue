<script setup lang="ts">
import { onMounted } from 'vue'
import { format } from 'date-fns'
import { useSessionsStore } from '@/stores/sessions'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import StatCard from '@/components/shared/StatCard.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const sessions = useSessionsStore()
const auth = useAuthStore()
const router = useRouter()
const tz = auth.user?.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone

onMounted(() => sessions.fetchWeek(format(new Date(), "yyyy-'W'ww"), tz))
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">My Sessions</h1>
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
      <StatCard label="This Week" :value="sessions.weekSessions.length" />
      <StatCard label="Live Now" :value="sessions.weekSessions.filter(s => s.status === 'live').length" />
      <StatCard label="Scheduled" :value="sessions.weekSessions.filter(s => s.status === 'scheduled').length" />
    </div>
    <div class="bg-card border border-border rounded-lg p-5">
      <h2 class="font-medium text-foreground mb-3">This Week's Sessions</h2>
      <div v-if="sessions.loading" class="text-muted-foreground text-sm py-4">Loading…</div>
      <div v-else-if="sessions.weekSessions.length === 0" class="text-muted-foreground text-sm py-4">No sessions this week.</div>
      <div v-else class="space-y-2">
        <div v-for="s in sessions.weekSessions" :key="s.id"
          class="flex items-center justify-between p-3 rounded hover:bg-accent cursor-pointer"
          @click="router.push(`/instructor/sessions/${s.id}`)">
          <div>
            <p class="text-sm font-medium text-foreground">{{ s.course_title }}</p>
            <p class="text-xs text-muted-foreground">{{ s.start_time.slice(0, 16).replace('T', ' ') }} · {{ s.room_name }}</p>
          </div>
          <StatusBadge :status="s.status" />
        </div>
      </div>
    </div>
  </AppLayout>
</template>
