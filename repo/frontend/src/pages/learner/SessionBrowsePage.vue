<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { format } from 'date-fns'
import { useSessionsStore } from '@/stores/sessions'
import { useBookingsStore } from '@/stores/bookings'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useCheckoutStore } from '@/stores/checkout'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import WeekCalendar from '@/components/calendar/WeekCalendar.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import SessionFlyout from '@/components/sessions/SessionFlyout.vue'
import LiveRoomModal from '@/components/live/LiveRoomModal.vue'
import type { Session } from '@/stores/sessions'

const sessions = useSessionsStore()
const bookings = useBookingsStore()
const auth = useAuthStore()
const ui = useUiStore()
const checkout = useCheckoutStore()
const router = useRouter()
const tz = auth.user?.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone

const view = ref<'calendar' | 'month' | 'list'>('calendar')
const currentMonth = ref(format(new Date(), 'yyyy-MM'))
const selectedSession = ref<Session | null>(null)
const liveSession = ref<Session | null>(null)

onMounted(() => {
  sessions.fetchWeek(format(new Date(), "yyyy-'W'ww"), tz)
  sessions.fetchMonth(currentMonth.value, tz)
})

function changeMonth(delta: number) {
  const [y, m] = currentMonth.value.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  currentMonth.value = format(d, 'yyyy-MM')
  sessions.fetchMonth(currentMonth.value, tz)
}

const monthDisplaySessions = computed(() =>
  sessions.monthlySessions.filter(s => s.status !== 'canceled')
)

async function handleBook(session: Session) {
  try {
    await checkout.createCart([{ session_id: session.id, quantity: 1 }])
    ui.addToast('Added to cart', 'success')
    router.push('/learner/checkout')
  } catch (e: any) { ui.addToast(e.message, 'error') }
}

const bookableStatuses = ['scheduled']
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Browse Sessions</h1>
      <div class="flex border border-border rounded overflow-hidden text-sm">
        <button v-for="v in ['calendar','month','list']" :key="v" @click="view = v as any" :class="['px-3 py-1.5', view === v ? 'bg-primary text-primary-foreground' : 'bg-background text-muted-foreground hover:text-foreground']">
          {{ v.charAt(0).toUpperCase() + v.slice(1) }}
        </button>
      </div>
    </div>

    <WeekCalendar v-if="view === 'calendar'" :sessions="sessions.weekSessions" :tz="tz"
      @week-change="(w) => sessions.fetchWeek(w, tz)"
      @session-click="selectedSession = $event"
    />

    <div v-else-if="view === 'month'">
      <div class="flex items-center justify-between mb-4">
        <button @click="changeMonth(-1)" class="px-3 py-1 rounded border border-border text-sm hover:bg-accent">&lsaquo; Prev</button>
        <span class="font-medium text-sm">{{ currentMonth }}</span>
        <button @click="changeMonth(1)" class="px-3 py-1 rounded border border-border text-sm hover:bg-accent">Next &rsaquo;</button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="s in monthDisplaySessions" :key="s.id"
          class="bg-card border border-border rounded-lg p-4 flex flex-col gap-3 hover:shadow-md transition-shadow">
          <div class="flex items-start justify-between">
            <h3 class="font-medium text-foreground text-sm">{{ s.course_title }}</h3>
            <StatusBadge :status="s.status" />
          </div>
          <div class="text-xs text-muted-foreground space-y-1">
            <div>{{ s.start_time.slice(0, 16).replace('T', ' ') }}</div>
            <div>{{ s.instructor_name }}</div>
            <div>{{ s.location_name }}</div>
            <div>{{ s.enrolled_count }}/{{ s.capacity }} enrolled</div>
          </div>
          <div class="flex gap-2 mt-auto pt-2">
            <button v-if="s.status === 'scheduled'" @click="handleBook(s)" class="flex-1 py-1.5 bg-primary text-primary-foreground rounded text-xs hover:opacity-90">Book Now</button>
            <button v-if="s.status === 'live'" @click="liveSession = s" class="flex-1 py-1.5 bg-green-600 text-white rounded text-xs hover:bg-green-700">Join Live</button>
            <button @click="$router.push(`/learner/sessions/${s.id}`)" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-xs hover:bg-accent">Details</button>
          </div>
        </div>
        <div v-if="!monthDisplaySessions.length" class="col-span-full text-center text-muted-foreground text-sm py-12">No sessions this month.</div>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="s in sessions.weekSessions.filter(x => x.status !== 'canceled')" :key="s.id"
        class="bg-card border border-border rounded-lg p-4 flex flex-col gap-3 hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <h3 class="font-medium text-foreground text-sm">{{ s.course_title }}</h3>
          <StatusBadge :status="s.status" />
        </div>
        <div class="text-xs text-muted-foreground space-y-1">
          <div>{{ s.start_time.slice(0, 16).replace('T', ' ') }}</div>
          <div>{{ s.instructor_name }}</div>
          <div>{{ s.location_name }}</div>
          <div>{{ s.enrolled_count }}/{{ s.capacity }} enrolled</div>
        </div>
        <div class="flex gap-2 mt-auto pt-2">
          <button v-if="s.status === 'scheduled'" @click="handleBook(s)" class="flex-1 py-1.5 bg-primary text-primary-foreground rounded text-xs hover:opacity-90">
            Book Now
          </button>
          <button v-if="s.status === 'live'" @click="liveSession = s" class="flex-1 py-1.5 bg-green-600 text-white rounded text-xs hover:bg-green-700">
            Join Live
          </button>
          <button @click="$router.push(`/learner/sessions/${s.id}`)" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-xs hover:bg-accent">
            Details
          </button>
        </div>
      </div>
    </div>

    <SessionFlyout :session="selectedSession" :tz="tz" @close="selectedSession = null"
      @book="handleBook" @live-room="liveSession = $event" @roster="() => {}" />

    <LiveRoomModal v-if="liveSession" :session="liveSession" @close="liveSession = null" />
  </AppLayout>
</template>
