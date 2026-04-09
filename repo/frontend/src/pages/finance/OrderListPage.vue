<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { checkoutApi } from '@/api/endpoints/checkout'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const orders = ref<any[]>([])
const total = ref(0)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await checkoutApi.getOrders({ page_size: 50 })
    orders.value = res.items
    total.value = res.total
  } finally { loading.value = false }
})

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">Orders ({{ total }})</h1>
    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Order ID</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Total</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Created</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="4" class="py-8 text-center text-muted-foreground">Loading…</td></tr>
          <tr v-for="o in orders" :key="o.id" class="border-t border-border hover:bg-muted/30">
            <td class="px-4 py-3 font-mono text-xs">{{ o.id.slice(0, 8) }}…</td>
            <td class="px-4 py-3"><StatusBadge :status="o.status" /></td>
            <td class="px-4 py-3 text-right font-medium">{{ fmt(o.total) }}</td>
            <td class="px-4 py-3 text-xs text-muted-foreground">{{ o.created_at?.slice(0, 16) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
