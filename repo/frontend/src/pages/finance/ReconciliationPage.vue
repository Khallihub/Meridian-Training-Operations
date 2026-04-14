<script setup lang="ts">
import { onMounted } from 'vue'
import { usePaymentsStore } from '@/stores/payments'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'
import { Download, RefreshCw } from 'lucide-vue-next'

const payments = usePaymentsStore()
const ui = useUiStore()

onMounted(() => payments.fetchExports())

async function generate() {
  try {
    const ex = await payments.triggerExport()
    ui.addToast(`Export for ${ex.export_date} generated (${ex.row_count} rows)`, 'success')
    payments.fetchExports()
  } catch (e: any) {
    ui.addToast(e.message ?? 'Export failed', 'error')
  }
}
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Reconciliation</h1>
      <button @click="generate" class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
        <RefreshCw class="h-4 w-4" /> Generate Today's Export
      </button>
    </div>

    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Date</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Rows</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Generated At</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Download</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="payments.exports.length === 0">
            <td colspan="4" class="py-8 text-center text-muted-foreground">No exports yet.</td>
          </tr>
          <tr v-for="ex in payments.exports" :key="ex.id" class="border-t border-border hover:bg-muted/30">
            <td class="px-4 py-3 font-medium">{{ ex.export_date }}</td>
            <td class="px-4 py-3 text-right text-muted-foreground">{{ ex.row_count.toLocaleString() }}</td>
            <td class="px-4 py-3 text-muted-foreground text-xs">{{ ex.generated_at.slice(0, 16) }}</td>
            <td class="px-4 py-3 text-right">
              <a :href="`/api/v1/reconciliation/exports/${ex.id}/download`" download class="flex items-center justify-end gap-1 text-primary hover:underline text-xs">
                <Download class="h-3.5 w-3.5" /> CSV
              </a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
