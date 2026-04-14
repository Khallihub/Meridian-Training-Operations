<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { format, addWeeks, subWeeks, startOfWeek, addDays, parseISO, differenceInMinutes } from 'date-fns'
import { formatInTimeZone } from 'date-fns-tz'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import type { Session } from '@/stores/sessions'

const props = defineProps<{
  sessions: Session[]
  loading?: boolean
  tz?: string
}>()

const emit = defineEmits<{
  (e: 'week-change', week: string): void
  (e: 'session-click', session: Session): void
}>()

const currentDate = ref(new Date())
const tz = computed(() => props.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone)

const weekStart = computed(() => startOfWeek(currentDate.value, { weekStartsOn: 1 }))
const weekDays = computed(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart.value, i)))
const weekLabel = computed(() => format(weekStart.value, "'Week of' MMM d, yyyy"))
const hours = Array.from({ length: 24 }, (_, i) => i)

// Emit week param on change
watch(weekStart, (d) => {
  emit('week-change', format(d, "yyyy-'W'ww"))
}, { immediate: true })

function prevWeek() { currentDate.value = subWeeks(currentDate.value, 1) }
function nextWeek() { currentDate.value = addWeeks(currentDate.value, 1) }

const statusColors: Record<string, string> = {
  scheduled: 'bg-blue-200 border-blue-400 text-blue-900',
  live: 'bg-green-200 border-green-400 text-green-900',
  ended: 'bg-gray-200 border-gray-400 text-gray-700',
  canceled: 'bg-red-100 border-red-300 text-red-700 line-through opacity-60',
}

// Group sessions by weekday index (0=Mon..6=Sun) using target timezone for day assignment.
const sessionsByDay = computed(() => {
  const groups: Record<number, Session[]> = {}
  for (let i = 0; i < 7; i++) groups[i] = []
  for (const s of props.sessions) {
    const sessionDayInTz = formatInTimeZone(parseISO(s.start_time), tz.value, 'yyyy-MM-dd')
    for (let i = 0; i < 7; i++) {
      const weekDayInTz = formatInTimeZone(weekDays.value[i], tz.value, 'yyyy-MM-dd')
      if (sessionDayInTz === weekDayInTz) {
        groups[i].push(s)
        break
      }
    }
  }
  return groups
})

function sessionTop(session: Session) {
  const timeInTz = formatInTimeZone(parseISO(session.start_time), tz.value, 'H:mm')
  const [h, m] = timeInTz.split(':').map(Number)
  return (h * 60 + m) / 60 * 48 // 48px per hour
}

function sessionHeight(session: Session) {
  const start = parseISO(session.start_time)
  const end = parseISO(session.end_time)
  const mins = differenceInMinutes(end, start)
  return Math.max(mins / 60 * 48, 24) // min 24px
}

function sessionLabel(session: Session) {
  return formatInTimeZone(parseISO(session.start_time), tz.value, 'h:mm a')
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <!-- Toolbar -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <button @click="prevWeek" class="p-1 rounded hover:bg-accent"><ChevronLeft class="h-4 w-4" /></button>
        <span class="text-sm font-medium">{{ weekLabel }}</span>
        <button @click="nextWeek" class="p-1 rounded hover:bg-accent"><ChevronRight class="h-4 w-4" /></button>
      </div>
      <slot name="toolbar" />
    </div>

    <!-- Grid -->
    <div class="overflow-auto max-h-[600px] border border-border rounded-lg">
      <div class="flex">
        <!-- Time gutter -->
        <div class="w-14 shrink-0 border-r border-border bg-muted/30">
          <div class="h-10 border-b border-border" /> <!-- header spacer -->
          <div v-for="h in hours" :key="h" class="h-12 border-b border-border/50 flex items-start justify-end pr-1 pt-0.5">
            <span class="text-xs text-muted-foreground">{{ h === 0 ? '12am' : h < 12 ? `${h}am` : h === 12 ? '12pm' : `${h-12}pm` }}</span>
          </div>
        </div>

        <!-- Day columns -->
        <div class="flex flex-1 divide-x divide-border">
          <div v-for="(day, dayIdx) in weekDays" :key="dayIdx" class="flex-1 min-w-[120px]">
            <!-- Day header -->
            <div class="h-10 border-b border-border flex flex-col items-center justify-center sticky top-0 bg-muted/30 z-10">
              <span class="text-xs font-medium text-muted-foreground">{{ format(day, 'EEE') }}</span>
              <span class="text-sm font-semibold text-foreground">{{ format(day, 'd') }}</span>
            </div>

            <!-- Session blocks (relative positioning) -->
            <div class="relative" :style="{ height: `${24 * 48}px` }">
              <!-- Hour lines -->
              <div v-for="h in hours" :key="h" class="absolute w-full border-b border-border/30" :style="{ top: `${h * 48}px` }" />

              <!-- Sessions -->
              <button
                v-for="session in sessionsByDay[dayIdx]"
                :key="session.id"
                :class="['absolute left-0.5 right-0.5 rounded text-xs px-1 overflow-hidden border cursor-pointer hover:opacity-80 transition-opacity text-left', statusColors[session.status]]"
                :style="{ top: `${sessionTop(session)}px`, height: `${sessionHeight(session)}px` }"
                @click="emit('session-click', session)"
              >
                <div class="font-medium truncate">{{ session.course_title }}</div>
                <div class="truncate opacity-80">{{ sessionLabel(session) }}</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
