<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { adminApi } from '@/api/endpoints/admin'
import AppLayout from '@/layouts/AppLayout.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()
const editId = route.params.id as string | undefined
const prefix = auth.isAdmin ? '/admin' : '/finance'

const form = ref({
  name: '', type: 'pct_off' as 'pct_off' | 'fixed_off' | 'bogo', value: 0,
  min_order_amount: '', applies_to: 'all' as const,
  stack_group: '', is_exclusive: false, is_active: true,
  valid_from: '', valid_until: '',
})

const previewResult = ref<any>(null)
const isSubmitting = ref(false)

onMounted(async () => {
  if (editId) {
    const promos = await adminApi.getPromotions()
    const p = promos.find(x => x.id === editId)
    if (p) Object.assign(form.value, { ...p, min_order_amount: p.min_order_amount ?? '', stack_group: p.stack_group ?? '' })
  }
})

async function handleSubmit() {
  isSubmitting.value = true
  const payload = {
    ...form.value,
    min_order_amount: form.value.min_order_amount ? Number(form.value.min_order_amount) : null,
    stack_group: form.value.stack_group || null,
  }
  try {
    if (editId) {
      await adminApi.updatePromotion(editId, payload)
      ui.addToast('Promotion updated', 'success')
    } else {
      await adminApi.createPromotion(payload)
      ui.addToast('Promotion created', 'success')
    }
    router.push(`${prefix}/promotions`)
  } catch (e: any) { ui.addToast(e.message, 'error') }
  finally { isSubmitting.value = false }
}

async function handlePreview() {
  previewResult.value = await adminApi.previewPromotion({ promotion: form.value, sample_order_total: 100 })
}
</script>

<template>
  <AppLayout>
    <div class="max-w-xl">
      <h1 class="text-xl font-semibold text-foreground mb-6">{{ editId ? 'Edit' : 'New' }} Promotion</h1>
      <div class="bg-card border border-border rounded-lg p-6">
        <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Name</label>
            <input v-model="form.name" required class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Type</label>
              <select v-model="form.type" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm">
                <option value="pct_off">Percent Off</option>
                <option value="fixed_off">Fixed Off</option>
                <option value="bogo">BOGO</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Value</label>
              <input v-model.number="form.value" type="number" step="0.01" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Min Order Amount</label>
            <input v-model="form.min_order_amount" type="number" step="0.01" placeholder="No minimum" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Stack Group (leave blank for singleton pool)</label>
            <input v-model="form.stack_group" type="text" placeholder="e.g. bundle-group" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm font-mono" />
            <p class="text-xs text-muted-foreground mt-1">Blank = mutual exclusion singleton pool. Same named group = exclusive within group. Different groups = stackable across groups.</p>
          </div>
          <div class="flex items-center gap-4">
            <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="form.is_exclusive" class="rounded" /> Exclusive (never stacks)</label>
            <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="form.is_active" class="rounded" /> Active</label>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Valid From</label>
              <input v-model="form.valid_from" type="datetime-local" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Valid Until</label>
              <input v-model="form.valid_until" type="datetime-local" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            </div>
          </div>
          <div class="flex gap-3 pt-2">
            <button type="submit" :disabled="isSubmitting" class="px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90 disabled:opacity-50">
              {{ editId ? 'Save' : 'Create' }}
            </button>
            <button type="button" @click="handlePreview" class="px-4 py-2 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">Preview Best Offer</button>
            <button type="button" @click="router.back()" class="px-4 py-2 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">Cancel</button>
          </div>
        </form>

        <!-- Preview result -->
        <div v-if="previewResult" class="mt-4 p-4 bg-muted/30 rounded-lg text-sm">
          <h3 class="font-medium mb-2">Preview Result</h3>
          <pre class="text-xs font-mono overflow-x-auto">{{ JSON.stringify(previewResult, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
