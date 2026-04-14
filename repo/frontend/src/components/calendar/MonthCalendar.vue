<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { format, startOfMonth, endOfMonth, startOfWeek, addDays, isSameMonth, parseISO, addMonths, subMonths } from 'date-fns'
import { formatInTimeZone } from 'date-fns-tz'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import type { Session } from '@/stores/sessions'

const props = defineProps<{
  sessions: Session[]
  tz?: string
}>()

const emit = defineEmits<{
  (e: 'month-change', month: string): void
  (e: 'session-click', session: Session): void
}>()

const currentDate = ref(new Date())
const monthLabel = computed(() => format(currentDate.value, 'MMMM yyyy'))

const calendarDays = computed(() => {
  const start = startOfWeek(startOfMonth(currentDate.value), { weekStartsOn: 1 })
  const end = addDays(startOfWeek(endOfMonth(currentDate.value), { weekStartsOn: 1 }), 6)
  const days: Date[] = []
  let d = start
  while (d <= end) { days.push(d); d = addDays(d, 1) }
  return days
})

watch(() => format(currentDate.value, 'yyyy-MM'), (m) => emit('month-change', m), { immediate: true })

function prevMonth() { currentDate.value = subMonths(currentDate.value, 1) }
function nextMonth() { currentDate.value = addMonths(currentDate.value, 1) }

const statusDot: Record<string, string> = {
  scheduled: 'bg-blue-400', live: 'bg-green-400', ended: 'bg-gray-400', canceled: 'bg-red-400',
}

const calendarTz = computed(() => props.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone)

function sessionsForDay(day: Date): Session[] {
  const key = formatInTimeZone(day, calendarTz.value, 'yyyy-MM-dd')
  return props.sessions.filter(s => {
    try {
      return formatInTimeZone(parseISO(s.start_time), calendarTz.value, 'yyyy-MM-dd') === key
    } catch {
      return false
    }
  })
}

const VISIBLE_MAX = 3
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <button @click="prevMonth" class="p-1 rounded hover:bg-accent"><ChevronLeft class="h-4 w-4" /></button>
        <span class="text-sm font-medium">{{ monthLabel }}</span>
        <button @click="nextMonth" class="p-1 rounded hover:bg-accent"><ChevronRight class="h-4 w-4" /></button>
      </div>
      <slot name="toolbar" />
    </div>

    <div class="border border-border rounded-lg overflow-hidden">
      <!-- Day headers -->
      <div class="grid grid-cols-7 bg-muted/50 border-b border-border">
        <div v-for="d in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']" :key="d" class="py-2 text-center text-xs font-medium text-muted-foreground">{{ d }}</div>
      </div>

      <!-- Calendar grid -->
      <div class="grid grid-cols-7">
        <div
          v-for="(day, i) in calendarDays"
          :key="i"
          :class="['min-h-[96px] p-1 border-b border-r border-border/50', !isSameMonth(day, currentDate) ? 'bg-muted/20' : '']"
        >
          <div :class="['text-xs font-medium mb-1', !isSameMonth(day, currentDate) ? 'text-muted-foreground' : 'text-foreground']">
            {{ format(day, 'd') }}
          </div>
          <div class="flex flex-col gap-0.5">
            <button
              v-for="(s, si) in sessionsForDay(day).slice(0, VISIBLE_MAX)"
              :key="s.id"
              :class="['flex items-center gap-1 w-full text-left text-xs rounded px-1 py-0.5 hover:bg-accent truncate']"
              @click="emit('session-click', s)"
            >
              <span :class="['h-1.5 w-1.5 rounded-full shrink-0', statusDot[s.status]]" />
              <span class="truncate">{{ s.course_title }}</span>
            </button>
            <button
              v-if="sessionsForDay(day).length > VISIBLE_MAX"
              class="text-xs text-primary hover:underline text-left px-1"
              @click="() => {}"
            >
              +{{ sessionsForDay(day).length - VISIBLE_MAX }} more
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
