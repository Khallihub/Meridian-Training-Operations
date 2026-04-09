<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionsStore } from '@/stores/sessions'
import { useUiStore } from '@/stores/ui'
import { sessionsApi } from '@/api/endpoints/sessions'
import AppLayout from '@/layouts/AppLayout.vue'
import { UserCheck, UserX } from 'lucide-vue-next'

const route = useRoute()
const sessions = useSessionsStore()
const ui = useUiStore()
const sessionId = route.params.id as string

const roster = ref<any[]>([])
const stats = ref<{ avg_minutes_attended: number; late_joins: number; replay_completion_rate: number } | null>(null)

onMounted(async () => {
  roster.value = await sessions.fetchRoster(sessionId)
  try { stats.value = await sessionsApi.getAttendanceStats(sessionId) } catch {}
})

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
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">Attendance</h1>

    <!-- Stats bar -->
    <div v-if="stats" class="grid grid-cols-3 gap-4 mb-6">
      <div class="bg-card border border-border rounded p-3 text-center">
        <p class="text-xs text-muted-foreground">Completion</p>
        <p class="text-xl font-semibold">{{ stats.replay_completion_rate }}%</p>
      </div>
      <div class="bg-card border border-border rounded p-3 text-center">
        <p class="text-xs text-muted-foreground">Avg Minutes</p>
        <p class="text-xl font-semibold">{{ stats.avg_minutes_attended }}</p>
      </div>
      <div class="bg-card border border-border rounded p-3 text-center">
        <p class="text-xs text-muted-foreground">Late Arrivals</p>
        <p class="text-xl font-semibold">{{ stats.late_joins }}</p>
      </div>
    </div>

    <!-- Roster -->
    <div class="overflow-x-auto rounded-lg border border-border">
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
                <button v-if="!learner.checked_in" @click="checkin(learner.id)" class="flex items-center gap-1 px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">
                  <UserCheck class="h-3 w-3" /> Check In
                </button>
                <button v-if="learner.checked_in && !learner.checked_out" @click="checkout(learner.id)" class="flex items-center gap-1 px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded hover:bg-accent">
                  <UserX class="h-3 w-3" /> Check Out
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
