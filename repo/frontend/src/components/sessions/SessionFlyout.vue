<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, Edit, XCircle, Radio, CheckCircle, Users } from 'lucide-vue-next'
import { formatInTimeZone } from 'date-fns-tz'
import { parseISO } from 'date-fns'
import type { Session } from '@/stores/sessions'
import { useAuthStore } from '@/stores/auth'
import { useSessionsStore } from '@/stores/sessions'
import { useUiStore } from '@/stores/ui'
import { useRouter } from 'vue-router'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const props = defineProps<{ session: Session | null; tz?: string }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'book', session: Session): void
  (e: 'live-room', session: Session): void
  (e: 'roster', session: Session): void
}>()

const auth = useAuthStore()
const sessions = useSessionsStore()
const ui = useUiStore()
const router = useRouter()
const tz = computed(() => props.tz ?? auth.user?.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone)

function fmt(dt: string) {
  return formatInTimeZone(parseISO(dt), tz.value, 'MMM d, yyyy h:mm a z')
}

async function handleGoLive() {
  if (!props.session) return
  try {
    await sessions.goLive(props.session.id)
    ui.addToast('Session is now live', 'success')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
}

async function handleComplete() {
  if (!props.session) return
  try {
    await sessions.complete(props.session.id)
    ui.addToast('Session completed', 'success')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
}

async function handleCancel() {
  if (!props.session) return
  try {
    await sessions.cancel(props.session.id)
    ui.addToast('Session cancelled', 'success')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
}

const capacityPct = computed(() => {
  if (!props.session) return 0
  return Math.round((props.session.enrolled_count / props.session.capacity) * 100)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="flyout">
      <div v-if="session" class="fixed inset-0 z-50 flex justify-end">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30" @click="emit('close')" />

        <!-- Sheet -->
        <div class="relative w-full max-w-md bg-card border-l border-border shadow-xl flex flex-col overflow-y-auto">
          <!-- Header -->
          <div class="flex items-center justify-between p-4 border-b border-border">
            <div>
              <h2 class="font-semibold text-foreground">{{ session.course_title }}</h2>
              <StatusBadge :status="session.status" class="mt-1" />
            </div>
            <button @click="emit('close')" class="p-1 rounded hover:bg-accent">
              <X class="h-5 w-5" />
            </button>
          </div>

          <!-- Content -->
          <div class="p-4 flex flex-col gap-4 flex-1">
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p class="text-muted-foreground">Instructor</p>
                <p class="font-medium">{{ session.instructor_name }}</p>
              </div>
              <div>
                <p class="text-muted-foreground">Room</p>
                <p class="font-medium">{{ session.room_name }}</p>
              </div>
              <div>
                <p class="text-muted-foreground">Location</p>
                <p class="font-medium">{{ session.location_name }}</p>
              </div>
              <div>
                <p class="text-muted-foreground">Capacity</p>
                <p class="font-medium">{{ session.enrolled_count }} / {{ session.capacity }}</p>
              </div>
            </div>

            <div class="text-sm">
              <p class="text-muted-foreground">Start</p>
              <p>{{ fmt(session.start_time) }}</p>
            </div>
            <div class="text-sm">
              <p class="text-muted-foreground">End</p>
              <p>{{ fmt(session.end_time) }}</p>
            </div>

            <!-- Capacity bar -->
            <div>
              <div class="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Enrollment</span><span>{{ capacityPct }}%</span>
              </div>
              <div class="h-2 bg-muted rounded-full overflow-hidden">
                <div :class="['h-full rounded-full transition-all', capacityPct >= 90 ? 'bg-red-500' : capacityPct >= 70 ? 'bg-yellow-500' : 'bg-green-500']" :style="{ width: `${capacityPct}%` }" />
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="p-4 border-t border-border flex flex-wrap gap-2">
            <!-- Admin / Instructor actions -->
            <template v-if="auth.isAdmin || auth.isInstructor">
              <button v-if="session.status === 'scheduled'" @click="handleGoLive" class="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700">
                <Radio class="h-3.5 w-3.5" /> Go Live
              </button>
              <button v-if="session.status === 'live'" @click="emit('live-room', session)" class="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700">
                <Radio class="h-3.5 w-3.5" /> Join Live Room
              </button>
              <button v-if="session.status === 'live'" @click="handleComplete" class="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                <CheckCircle class="h-3.5 w-3.5" /> Complete
              </button>
              <button v-if="auth.isAdmin" @click="router.push(`/admin/sessions/${session.id}/edit`)" class="flex items-center gap-1 px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">
                <Edit class="h-3.5 w-3.5" /> Edit
              </button>
              <button v-if="['scheduled','live'].includes(session.status)" @click="handleCancel" class="flex items-center gap-1 px-3 py-1.5 bg-destructive/10 text-destructive rounded text-sm hover:bg-destructive/20">
                <XCircle class="h-3.5 w-3.5" /> Cancel
              </button>
            </template>

            <!-- Learner actions -->
            <template v-if="auth.isLearner">
              <button v-if="session.status === 'scheduled'" @click="emit('book', session)" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
                Book Now
              </button>
              <button v-if="session.status === 'live'" @click="emit('live-room', session)" class="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700">
                Join Live Room
              </button>
            </template>

            <!-- Roster (all roles) -->
            <button @click="emit('roster', session)" class="flex items-center gap-1 px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">
              <Users class="h-3.5 w-3.5" /> Roster
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.flyout-enter-active, .flyout-leave-active { transition: transform 0.25s ease; }
.flyout-enter-from, .flyout-leave-to { transform: translateX(100%); }
</style>
