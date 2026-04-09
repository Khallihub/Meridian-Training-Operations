<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePaymentsStore } from '@/stores/payments'
import AppLayout from '@/layouts/AppLayout.vue'
import StatCard from '@/components/shared/StatCard.vue'

const payments = usePaymentsStore()
const pendingRefundsCount = ref(0)

onMounted(async () => {
  await Promise.all([
    payments.fetchRefunds('pending'),
    payments.fetchExports(),
  ])
  pendingRefundsCount.value = payments.refunds.length
})
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">Finance Dashboard</h1>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <StatCard label="Pending Refunds" :value="pendingRefundsCount" />
      <StatCard label="Export Files" :value="payments.exports.length" />
      <StatCard label="Latest Export" :value="payments.exports[0]?.export_date ?? '—'" />
      <StatCard label="Last Export Rows" :value="payments.exports[0]?.row_count ?? 0" />
    </div>

    <!-- Quick links -->
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <RouterLink v-for="[label, to] in [['Refunds', '/finance/refunds'], ['Payments', '/finance/payments'], ['Reconciliation', '/finance/reconciliation'], ['Promotions', '/finance/promotions'], ['Search', '/finance/search']]" :key="to"
        :to="to"
        class="p-4 bg-card border border-border rounded-lg hover:bg-accent transition-colors text-sm font-medium text-foreground"
      >{{ label }}</RouterLink>
    </div>
  </AppLayout>
</template>
