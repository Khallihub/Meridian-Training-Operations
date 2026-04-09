<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useBookingsStore } from '@/stores/bookings'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { formatInTimeZone } from 'date-fns-tz'
import { parseISO } from 'date-fns'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import DataTable from '@/components/tables/DataTable.vue'
import type { Column } from '@/components/tables/DataTable.vue'

const bookings = useBookingsStore()
const auth = useAuthStore()
const ui = useUiStore()

const filterStatus = ref('')
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone

function fmtDate(v: unknown) {
  if (!v) return '—'
  try { return formatInTimeZone(parseISO(String(v)), tz, 'MMM d, yyyy h:mm a') }
  catch { return String(v) }
}
const historyBookingId = ref<string | null>(null)

const page = ref(1)
const pageSize = ref(25)

const columns = computed<Column[]>(() => {
  const cols: Column[] = [
    { key: 'session_title', label: 'Session' },
    { key: 'session_start_time', label: 'Date' },
    { key: 'status', label: 'Status' },
    { key: 'policy_fee_flagged', label: 'Cancellation Fee' },
  ]
  if (auth.isAdmin) cols.splice(2, 0, { key: 'learner_username', label: 'Learner' })
  return cols
})

onMounted(() => loadBookings())

function loadBookings() {
  bookings.fetchAll({
    status: filterStatus.value || undefined,
    page: page.value,
    page_size: pageSize.value,
  })
}

async function handleConfirm(id: string) {
  try { await bookings.confirm(id); ui.addToast('Booking confirmed', 'success') }
  catch (e: any) { ui.addToast(e.message, 'error') }
}

async function handleCancel(id: string) {
  const reason = prompt('Cancellation reason (optional)')
  try {
    const b = await bookings.cancel(id, reason ?? undefined)
    if (b.policy_fee_flagged) ui.addToast('Booking cancelled. Cancellation fee applies.', 'warning')
    else ui.addToast('Booking cancelled', 'success')
  } catch (e: any) { ui.addToast(e.message, 'error') }
}
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">Bookings</h1>

    <!-- Filter -->
    <div class="flex gap-3 mb-4">
      <select v-model="filterStatus" @change="loadBookings" class="px-2 py-1.5 rounded border border-border bg-background text-sm">
        <option value="">All statuses</option>
        <option>pending</option><option>confirmed</option><option>rescheduled</option><option>cancelled</option><option>no_show</option>
      </select>
    </div>

    <DataTable
      :columns="columns"
      :rows="(bookings.bookings as any[])"
      :loading="bookings.loading"
      :total-count="bookings.totalCount"
      :page-size="pageSize"
      :current-page="page"
      @page-change="(p) => { page = p; loadBookings() }"
      @size-change="(s) => { pageSize = s; page = 1; loadBookings() }"
      empty-title="No bookings found"
    >
      <template #cell-session_start_time="{ value }">
        {{ fmtDate(value) }}
      </template>
      <template #cell-status="{ value }">
        <StatusBadge :status="String(value)" />
      </template>
      <template #cell-policy_fee_flagged="{ value }">
        <span v-if="value" class="text-xs text-yellow-600 dark:text-yellow-400 font-medium">⚠ Fee</span>
      </template>
      <template #actions="{ row }">
        <div class="flex justify-end gap-1.5">
          <button v-if="auth.isAdmin && row.status === 'pending'" @click.stop="handleConfirm(String(row.id))" class="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">Confirm</button>
          <button v-if="['pending','confirmed'].includes(String(row.status))" @click.stop="handleCancel(String(row.id))" class="px-2 py-1 text-xs bg-destructive/10 text-destructive rounded hover:bg-destructive/20">Cancel</button>
        </div>
      </template>
    </DataTable>
  </AppLayout>
</template>
