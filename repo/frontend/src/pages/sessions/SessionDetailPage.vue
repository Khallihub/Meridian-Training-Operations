<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionsStore } from '@/stores/sessions'
import { useBookingsStore } from '@/stores/bookings'
import { useCheckoutStore } from '@/stores/checkout'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { sessionsApi } from '@/api/endpoints/sessions'
import { bookingsApi } from '@/api/endpoints/bookings'
import { formatInTimeZone } from 'date-fns-tz'
import { parseISO } from 'date-fns'
import { UserCheck, UserX } from 'lucide-vue-next'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import LiveRoomModal from '@/components/live/LiveRoomModal.vue'

const route = useRoute()
const router = useRouter()
const sessions = useSessionsStore()
const bookings = useBookingsStore()
const checkoutStore = useCheckoutStore()
const auth = useAuthStore()
const ui = useUiStore()

const sessionId = route.params.id as string
const activeTab = ref<'info' | 'roster' | 'attendance' | 'replay'>('info')

// Roster / attendance
const roster = ref<Array<{ id: string; username: string; checked_in: boolean; checked_out: boolean }>>([])
const rosterLoaded = ref(false)
const attendanceStats = ref<{ total_enrolled: number; checked_in: number; late_joins: number; avg_minutes_attended: number } | null>(null)

// Replay state
const replayLoading = ref(false)
const replayExpired = ref(false)
const replayAccessDenied = ref(false)
const recordings = ref<Array<{ id: string; mime_type: string; file_size_bytes: number | null; duration_seconds: number | null; created_at: string }>>([])
const showLiveRoom = ref(false)
const myBooking = ref<{ id: string; status: string } | null>(null)

const tz = computed(() => auth.user?.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone)

onMounted(async () => {
  await sessions.fetchOne(sessionId)
  if (auth.isLearner) {
    const res = await bookingsApi.getAll({ session_id: sessionId, page_size: 5 })
    myBooking.value = res.items.find((b: any) => b.status !== 'cancelled') ?? null
  }
})

// ── Roster ────────────────────────────────────────────────────────────────────
async function loadRoster() {
  if (rosterLoaded.value) return
  try {
    roster.value = await sessionsApi.getRoster(sessionId)
    rosterLoaded.value = true
  } catch (e: any) {
    ui.addToast(e.message ?? 'Failed to load roster', 'error')
  }
}

function handleTabRoster() {
  activeTab.value = 'roster'
  loadRoster()
}

// ── Attendance ────────────────────────────────────────────────────────────────
async function loadAttendance() {
  await loadRoster()
  try {
    attendanceStats.value = await sessionsApi.getAttendanceStats(sessionId)
  } catch {}
}

function handleTabAttendance() {
  activeTab.value = 'attendance'
  loadAttendance()
}

async function checkin(learnerId: string) {
  try {
    await sessionsApi.checkin(sessionId, learnerId)
    const learner = roster.value.find(l => l.id === learnerId)
    if (learner) learner.checked_in = true
    ui.addToast('Checked in', 'success')
  } catch (e: any) { ui.addToast(e.message, 'error') }
}

async function checkout(learnerId: string) {
  try {
    await sessionsApi.checkout(sessionId, learnerId)
    const learner = roster.value.find(l => l.id === learnerId)
    if (learner) learner.checked_out = true
    ui.addToast('Checked out', 'success')
  } catch (e: any) { ui.addToast(e.message, 'error') }
}

// ── Replay ────────────────────────────────────────────────────────────────────
async function loadReplay() {
  replayLoading.value = true
  replayExpired.value = false
  replayAccessDenied.value = false
  recordings.value = []
  try {
    recordings.value = await sessionsApi.getRecordings(sessionId)
  } catch (e: any) {
    if (e.statusCode === 410) {
      replayExpired.value = true
    } else if (e.statusCode === 403) {
      replayAccessDenied.value = true
    } else {
      ui.addToast(e.message ?? 'Failed to load recordings', 'error')
    }
  } finally {
    replayLoading.value = false
  }
}

function streamUrl(recordingId: string): string {
  return sessionsApi.recordingStreamUrl(sessionId, recordingId, auth.accessToken ?? '')
}

function fmtSize(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function fmtDuration(secs: number | null): string {
  if (!secs) return '—'
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function handleTabReplay() {
  activeTab.value = 'replay'
  if (recordings.value.length === 0 && !replayExpired.value && !replayAccessDenied.value) loadReplay()
}

// ── Booking (learner) ────────────────────────────────────────────────────────
async function handleBook() {
  try {
    await checkoutStore.createCart([{ session_id: sessionId, quantity: 1 }])
    router.push('/learner/checkout')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
}

async function handleCancelBooking() {
  if (!myBooking.value) return
  try {
    await bookings.cancel(myBooking.value.id)
    myBooking.value = null
    ui.addToast('Booking cancelled', 'success')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
}

const session = computed(() => sessions.currentSession)
</script>

<template>
  <AppLayout>
    <LoadingSpinner v-if="sessions.loading && !session" class="py-16" />

    <template v-else-if="session">
      <!-- Header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <h1 class="text-xl font-semibold text-foreground">{{ session.title }}</h1>
          <div class="flex items-center gap-2 mt-1">
            <StatusBadge :status="session.status" />
            <span class="text-sm text-muted-foreground">{{ session.location_name }} · {{ session.room_name }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-2">
          <!-- Learner -->
          <template v-if="auth.isLearner">
            <template v-if="session.status === 'scheduled'">
              <span v-if="myBooking" class="px-4 py-2 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded text-sm font-medium">
                Booked ({{ myBooking.status }})
              </span>
              <button v-if="myBooking" @click="handleCancelBooking" class="px-4 py-2 bg-destructive/10 text-destructive rounded text-sm hover:bg-destructive/20">
                Cancel Booking
              </button>
              <button v-else @click="handleBook" class="px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
                Book Now
              </button>
            </template>
            <button v-if="session.status === 'live'" @click="showLiveRoom = true" class="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700">
              Join Live Room
            </button>
          </template>
          <!-- Instructor / Admin -->
          <template v-if="auth.isInstructor || auth.isAdmin">
            <button v-if="session.status === 'live'" @click="showLiveRoom = true" class="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700">
              Join Live Room
            </button>
          </template>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-border mb-6 gap-4">
        <button @click="activeTab = 'info'"
          :class="['pb-2 text-sm font-medium transition-colors border-b-2 -mb-px', activeTab === 'info' ? 'text-primary border-primary' : 'text-muted-foreground border-transparent hover:text-foreground']">Info</button>
        <button v-if="auth.isAdmin || auth.isInstructor" @click="handleTabRoster()"
          :class="['pb-2 text-sm font-medium transition-colors border-b-2 -mb-px', activeTab === 'roster' ? 'text-primary border-primary' : 'text-muted-foreground border-transparent hover:text-foreground']">Roster</button>
        <button v-if="auth.isAdmin || auth.isInstructor" @click="handleTabAttendance()"
          :class="['pb-2 text-sm font-medium transition-colors border-b-2 -mb-px', activeTab === 'attendance' ? 'text-primary border-primary' : 'text-muted-foreground border-transparent hover:text-foreground']">Attendance</button>
        <button @click="handleTabReplay()"
          :class="['pb-2 text-sm font-medium transition-colors border-b-2 -mb-px', activeTab === 'replay' ? 'text-primary border-primary' : 'text-muted-foreground border-transparent hover:text-foreground']">Replay</button>
      </div>

      <!-- Tab: Info -->
      <div v-if="activeTab === 'info'" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-card border border-border rounded-lg p-5 space-y-3">
          <div v-for="[label, val] in [
            ['Course', session.course_title ?? '—'],
            ['Instructor', session.instructor_name ?? '—'],
            ['Location', session.location_name ?? '—'],
            ['Room', session.room_name ?? '—'],
            ['Start', formatInTimeZone(parseISO(session.start_time), tz, 'PPpp')],
            ['End', formatInTimeZone(parseISO(session.end_time), tz, 'PPpp')],
            ['Enrolled', `${session.enrolled_count} / ${session.capacity}`],
            ['Buffer', `${session.buffer_minutes} min`],
          ]" :key="label" class="flex justify-between text-sm">
            <span class="text-muted-foreground">{{ label }}</span>
            <span class="font-medium text-right">{{ val }}</span>
          </div>
        </div>
      </div>

      <!-- Tab: Roster -->
      <div v-else-if="activeTab === 'roster'">
        <div v-if="roster.length === 0" class="text-sm text-muted-foreground py-8 text-center">No enrolled learners.</div>
        <div v-else class="overflow-x-auto rounded-lg border border-border">
          <table class="w-full text-sm">
            <thead class="bg-muted/50">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-muted-foreground">Learner</th>
                <th class="px-4 py-3 text-left font-medium text-muted-foreground">Attendance</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="learner in roster" :key="learner.id" class="border-t border-border">
                <td class="px-4 py-3 font-medium text-foreground">{{ learner.username }}</td>
                <td class="px-4 py-3 text-xs text-muted-foreground">
                  {{ learner.checked_in ? (learner.checked_out ? 'Left' : 'Present') : 'Not checked in' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tab: Attendance -->
      <div v-else-if="activeTab === 'attendance'" class="flex flex-col gap-4">
        <!-- Stats -->
        <div v-if="attendanceStats" class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="bg-card border border-border rounded p-3 text-center">
            <p class="text-xs text-muted-foreground">Enrolled</p>
            <p class="text-xl font-semibold">{{ attendanceStats.total_enrolled }}</p>
          </div>
          <div class="bg-card border border-border rounded p-3 text-center">
            <p class="text-xs text-muted-foreground">Checked In</p>
            <p class="text-xl font-semibold">{{ attendanceStats.checked_in }}</p>
          </div>
          <div class="bg-card border border-border rounded p-3 text-center">
            <p class="text-xs text-muted-foreground">Late Arrivals</p>
            <p class="text-xl font-semibold">{{ attendanceStats.late_joins }}</p>
          </div>
          <div class="bg-card border border-border rounded p-3 text-center">
            <p class="text-xs text-muted-foreground">Avg Minutes</p>
            <p class="text-xl font-semibold">{{ Math.round(attendanceStats.avg_minutes_attended) }}</p>
          </div>
        </div>
        <!-- Checkin table -->
        <div v-if="roster.length === 0" class="text-sm text-muted-foreground py-8 text-center">No enrolled learners.</div>
        <div v-else class="overflow-x-auto rounded-lg border border-border">
          <table class="w-full text-sm">
            <thead class="bg-muted/50">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-muted-foreground">Learner</th>
                <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                <th class="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="learner in roster" :key="learner.id" class="border-t border-border hover:bg-muted/30">
                <td class="px-4 py-3 font-medium text-foreground">{{ learner.username }}</td>
                <td class="px-4 py-3 text-xs text-muted-foreground">
                  {{ learner.checked_in ? (learner.checked_out ? 'Left' : 'Present') : 'Not checked in' }}
                </td>
                <td class="px-4 py-3 text-right">
                  <div class="flex justify-end gap-2">
                    <button v-if="!learner.checked_in" @click="checkin(learner.id)"
                      class="flex items-center gap-1 px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">
                      <UserCheck class="h-3 w-3" /> Check In
                    </button>
                    <button v-if="learner.checked_in && !learner.checked_out" @click="checkout(learner.id)"
                      class="flex items-center gap-1 px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded hover:bg-accent">
                      <UserX class="h-3 w-3" /> Check Out
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tab: Replay -->
      <div v-else-if="activeTab === 'replay'" class="flex flex-col gap-4">
        <LoadingSpinner v-if="replayLoading" class="py-8" />

        <!-- Expired -->
        <div v-else-if="replayExpired" class="flex flex-col items-center py-16 text-center">
          <div class="h-14 w-14 rounded-full bg-muted flex items-center justify-center mb-4">
            <svg class="h-7 w-7 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="font-medium text-foreground">Replay access has expired</h3>
          <p class="text-sm text-muted-foreground mt-1">The replay window for this session has closed.</p>
        </div>

        <!-- Access denied -->
        <div v-else-if="replayAccessDenied" class="flex flex-col items-center py-16 text-center">
          <div class="h-14 w-14 rounded-full bg-muted flex items-center justify-center mb-4">
            <svg class="h-7 w-7 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m0 0v2m0-2h2m-2 0H10m2-6a4 4 0 100-8 4 4 0 000 8z" />
            </svg>
          </div>
          <h3 class="font-medium text-foreground">Replay not available</h3>
          <p class="text-sm text-muted-foreground mt-1">You don't have access to this replay.</p>
        </div>

        <!-- Recordings list -->
        <template v-else-if="recordings.length > 0">
          <div v-for="(rec, idx) in recordings" :key="rec.id" class="flex flex-col gap-2">
            <div class="flex items-center justify-between text-sm text-muted-foreground">
              <span class="font-medium text-foreground">Recording {{ recordings.length - idx }}</span>
              <span>{{ formatInTimeZone(parseISO(rec.created_at), tz, 'MMM d, yyyy h:mm a') }} · {{ fmtDuration(rec.duration_seconds) }} · {{ fmtSize(rec.file_size_bytes) }}</span>
            </div>
            <video
              :src="streamUrl(rec.id)"
              controls
              preload="metadata"
              class="w-full max-w-3xl rounded-lg border border-border bg-black"
              style="max-height: 480px"
            >
              Your browser does not support the video element.
            </video>
          </div>
        </template>

        <!-- No recordings yet -->
        <div v-else class="text-sm text-muted-foreground py-8 text-center">
          No recording is available for this session yet.
        </div>
      </div>
    </template>

    <!-- Live Room Modal -->
    <LiveRoomModal v-if="showLiveRoom && session" :session="session" @close="showLiveRoom = false" />
  </AppLayout>
</template>
