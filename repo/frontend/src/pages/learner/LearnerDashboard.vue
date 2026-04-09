<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { format } from 'date-fns'
import { useSessionsStore } from '@/stores/sessions'
import { useBookingsStore } from '@/stores/bookings'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import StatCard from '@/components/shared/StatCard.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const sessions = useSessionsStore()
const bookings = useBookingsStore()
const auth = useAuthStore()
const router = useRouter()
const tz = auth.user?.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone

onMounted(async () => {
  await Promise.all([
    sessions.fetchWeek(format(new Date(), "yyyy-'W'ww"), tz),
    bookings.fetchAll({ page_size: 5 }),
  ])
})

const upcomingSessions = computed(() =>
  sessions.weekSessions.filter(s => s.status === 'scheduled' || s.status === 'live').slice(0, 5)
)
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">My Dashboard</h1>

    <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
      <StatCard label="My Bookings" :value="bookings.totalCount" />
      <StatCard label="Upcoming" :value="upcomingSessions.length" />
      <StatCard label="Active Now" :value="sessions.weekSessions.filter(s => s.status === 'live').length" />
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Upcoming sessions -->
      <div class="bg-card border border-border rounded-lg p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-medium text-foreground">Upcoming Sessions</h2>
          <RouterLink to="/learner/sessions" class="text-xs text-primary hover:underline">Browse all</RouterLink>
        </div>
        <div v-if="upcomingSessions.length === 0" class="text-sm text-muted-foreground py-4 text-center">No upcoming sessions.</div>
        <div v-else class="space-y-2">
          <div v-for="s in upcomingSessions" :key="s.id" @click="router.push(`/learner/sessions/${s.id}`)"
            class="flex items-center justify-between p-2 rounded hover:bg-accent cursor-pointer">
            <div>
              <p class="text-sm font-medium text-foreground">{{ s.course_title }}</p>
              <p class="text-xs text-muted-foreground">{{ s.start_time.slice(0, 16).replace('T', ' ') }}</p>
            </div>
            <StatusBadge :status="s.status" />
          </div>
        </div>
      </div>

      <!-- Recent bookings -->
      <div class="bg-card border border-border rounded-lg p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-medium text-foreground">Recent Bookings</h2>
          <RouterLink to="/learner/bookings" class="text-xs text-primary hover:underline">View all</RouterLink>
        </div>
        <div v-if="bookings.bookings.length === 0" class="text-sm text-muted-foreground py-4 text-center">No bookings yet.</div>
        <div v-else class="space-y-2">
          <div v-for="b in bookings.bookings.slice(0, 5)" :key="b.id" class="flex items-center justify-between p-2 rounded">
            <p class="text-sm text-foreground truncate">{{ b.session_title }}</p>
            <StatusBadge :status="b.status" />
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
