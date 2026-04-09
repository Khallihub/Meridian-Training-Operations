<script setup lang="ts">
import { ref, onMounted } from 'vue'
import client from '@/api/client'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const payments = ref<any[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await client.get('/api/payments', { params: { page_size: 50 } })
    payments.value = res.data.items
  } finally { loading.value = false }
})

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">Payments</h1>
    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Terminal Ref</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Amount</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Sig Verified</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Received</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="5" class="py-8 text-center text-muted-foreground">Loading…</td></tr>
          <tr v-for="p in payments" :key="p.id" class="border-t border-border hover:bg-muted/30">
            <td class="px-4 py-3 font-mono text-xs">{{ p.terminal_ref ?? '—' }}</td>
            <td class="px-4 py-3 text-right font-medium">{{ fmt(p.amount) }}</td>
            <td class="px-4 py-3"><StatusBadge :status="p.status" /></td>
            <td class="px-4 py-3 text-xs" :class="p.signature_verified ? 'text-green-600' : 'text-yellow-600'">{{ p.signature_verified ? '✓' : '—' }}</td>
            <td class="px-4 py-3 text-xs text-muted-foreground">{{ p.callback_received_at?.slice(0, 16) ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
