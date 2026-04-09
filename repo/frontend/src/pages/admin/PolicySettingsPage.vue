<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'
import client from '@/api/client'

const ui = useUiStore()

interface Policy {
  reschedule_cutoff_hours: number
  cancellation_fee_hours: number
}

const policy = ref<Policy>({ reschedule_cutoff_hours: 2, cancellation_fee_hours: 24 })
const saving = ref(false)

onMounted(async () => {
  try {
    const res = await client.get('/api/admin/policy')
    policy.value = res.data
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
})

async function save() {
  saving.value = true
  try {
    const res = await client.patch('/api/admin/policy', {
      reschedule_cutoff_hours: policy.value.reschedule_cutoff_hours,
      cancellation_fee_hours: policy.value.cancellation_fee_hours,
    })
    policy.value = res.data
    ui.addToast('Policy saved', 'success')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="max-w-lg">
      <h1 class="text-xl font-semibold text-foreground mb-6">Booking Policy Settings</h1>

      <div class="bg-card border border-border rounded-lg p-6 space-y-6">
        <div>
          <label class="block text-sm font-medium text-foreground mb-1">
            Reschedule cutoff (hours before session start)
          </label>
          <p class="text-xs text-muted-foreground mb-2">
            Learners cannot reschedule within this many hours of the session start time.
          </p>
          <input
            v-model.number="policy.reschedule_cutoff_hours"
            type="number" min="0" max="168"
            class="w-32 rounded border border-border bg-background px-3 py-1.5 text-sm"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground mb-1">
            Cancellation fee window (hours before session start)
          </label>
          <p class="text-xs text-muted-foreground mb-2">
            Cancellations within this window are flagged for a cancellation fee.
          </p>
          <input
            v-model.number="policy.cancellation_fee_hours"
            type="number" min="0" max="168"
            class="w-32 rounded border border-border bg-background px-3 py-1.5 text-sm"
          />
        </div>

        <button
          @click="save"
          :disabled="saving"
          class="px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90 disabled:opacity-50"
        >
          {{ saving ? 'Saving…' : 'Save Policy' }}
        </button>
      </div>
    </div>
  </AppLayout>
</template>
