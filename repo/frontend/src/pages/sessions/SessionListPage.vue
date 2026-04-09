<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { format } from 'date-fns'
import { useRouter, useRoute } from 'vue-router'
import { useSessionsStore } from '@/stores/sessions'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/layouts/AppLayout.vue'
import WeekCalendar from '@/components/calendar/WeekCalendar.vue'
import MonthCalendar from '@/components/calendar/MonthCalendar.vue'
import SessionFlyout from '@/components/sessions/SessionFlyout.vue'
import LiveRoomModal from '@/components/live/LiveRoomModal.vue'
import type { Session } from '@/stores/sessions'
import { Plus, Calendar, List } from 'lucide-vue-next'

const sessions = useSessionsStore()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const view = ref<'week' | 'month' | 'list'>('week')
const selectedSession = ref<Session | null>(null)
const liveRoomSession = ref<Session | null>(null)
const tz = computed(() => auth.user?.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone)

const prefix = computed(() => route.path.startsWith('/admin') ? '/admin' : '/instructor')

function handleWeekChange(week: string) {
  sessions.fetchWeek(week, tz.value)
}

function handleMonthChange(month: string) {
  sessions.fetchMonth(month, tz.value)
}

onMounted(() => {
  const week = format(new Date(), "yyyy-'W'ww")
  sessions.fetchWeek(week, tz.value)
})
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Sessions</h1>
      <div class="flex items-center gap-2">
        <!-- View toggle -->
        <div class="flex border border-border rounded overflow-hidden">
          <button v-for="v in (['week','month'] as const)" :key="v"
            @click="view = v"
            :class="['px-3 py-1.5 text-sm', view === v ? 'bg-primary text-primary-foreground' : 'bg-background text-muted-foreground hover:text-foreground']"
          >
            {{ v.charAt(0).toUpperCase() + v.slice(1) }}
          </button>
        </div>
        <button v-if="auth.isAdmin" @click="router.push(`${prefix}/sessions/new`)" class="flex items-center gap-1 px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
          <Plus class="h-4 w-4" /> New Session
        </button>
      </div>
    </div>

    <WeekCalendar
      v-if="view === 'week'"
      :sessions="sessions.weekSessions"
      :loading="sessions.loading"
      :tz="tz"
      @week-change="handleWeekChange"
      @session-click="selectedSession = $event"
    />
    <MonthCalendar
      v-else
      :sessions="sessions.monthlySessions"
      :tz="tz"
      @month-change="handleMonthChange"
      @session-click="selectedSession = $event"
    />

    <SessionFlyout
      :session="selectedSession"
      :tz="tz"
      @close="selectedSession = null"
      @book="() => {}"
      @live-room="liveRoomSession = $event; selectedSession = null"
      @roster="router.push(`${prefix}/sessions/${$event.id}`)"
    />

    <LiveRoomModal
      v-if="liveRoomSession"
      :session="liveRoomSession"
      @close="liveRoomSession = null"
    />
  </AppLayout>
</template>
