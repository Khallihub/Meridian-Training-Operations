<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePaymentsStore } from '@/stores/payments'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const payments = usePaymentsStore()
const ui = useUiStore()
const activeTab = ref<'requested' | 'pending_review' | 'approved' | 'processing' | 'completed' | 'rejected' | 'failed' | 'canceled'>('requested')

onMounted(() => loadRefunds())

function loadRefunds() { payments.fetchRefunds(activeTab.value) }

async function handleReview(id: string) {
  try { await payments.reviewRefund(id); ui.addToast('Refund moved to review', 'success'); loadRefunds() }
  catch (e: any) { ui.addToast(e.message, 'error') }
}

async function handleApprove(id: string) {
  try { await payments.approveRefund(id); ui.addToast('Refund approved', 'success'); loadRefunds() }
  catch (e: any) { ui.addToast(e.message, 'error') }
}

async function handleReject(id: string) {
  try { await payments.rejectRefund(id); ui.addToast('Refund rejected', 'info'); loadRefunds() }
  catch (e: any) { ui.addToast(e.message, 'error') }
}

async function handleProcess(id: string) {
  try { await payments.processRefund(id); ui.addToast('Refund processing started', 'success'); loadRefunds() }
  catch (e: any) { ui.addToast(e.message, 'error') }
}

async function handleComplete(id: string) {
  try { await payments.completeRefund(id); ui.addToast('Refund completed', 'success'); loadRefunds() }
  catch (e: any) { ui.addToast(e.message, 'error') }
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}
</script>

<template>
  <AppLayout>
    <h1 class="text-xl font-semibold text-foreground mb-6">Refunds</h1>

    <div class="flex gap-2 mb-4 border-b border-border overflow-x-auto">
      <button v-for="tab in ['requested','pending_review','approved','processing','completed','rejected','failed','canceled']" :key="tab"
        @click="() => { activeTab = tab as any; loadRefunds() }"
        :class="['pb-2 px-3 text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap', activeTab === tab ? 'text-primary border-primary' : 'text-muted-foreground border-transparent hover:text-foreground']"
      >{{ tab.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }}</button>
    </div>

    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">ID</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Amount</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Reason</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Created</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="payments.loading"><td colspan="6" class="py-8 text-center text-muted-foreground">Loading…</td></tr>
          <tr v-else-if="payments.refunds.length === 0"><td colspan="6" class="py-8 text-center text-muted-foreground">No refunds.</td></tr>
          <tr v-for="r in payments.refunds" :key="r.id" class="border-t border-border hover:bg-muted/30">
            <td class="px-4 py-3 font-mono text-xs">{{ r.id.slice(0, 8) }}…</td>
            <td class="px-4 py-3">{{ fmt(r.amount) }}</td>
            <td class="px-4 py-3 text-muted-foreground max-w-xs truncate">{{ r.reason }}</td>
            <td class="px-4 py-3"><StatusBadge :status="r.status" /></td>
            <td class="px-4 py-3 text-xs text-muted-foreground">{{ r.created_at.slice(0, 10) }}</td>
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end gap-2 flex-wrap">
                <button v-if="r.status === 'requested'" @click="handleReview(r.id)" class="px-2 py-1 text-xs bg-yellow-600 text-white rounded hover:bg-yellow-700">Review</button>
                <button v-if="r.status === 'pending_review'" @click="handleApprove(r.id)" class="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">Approve</button>
                <button v-if="r.status === 'pending_review'" @click="handleReject(r.id)" class="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700">Reject</button>
                <button v-if="r.status === 'approved'" @click="handleProcess(r.id)" class="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">Process</button>
                <button v-if="r.status === 'processing'" @click="handleComplete(r.id)" class="px-2 py-1 text-xs bg-teal-600 text-white rounded hover:bg-teal-700">Complete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
