<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { adminApi, type Promotion } from '@/api/endpoints/admin'
import AppLayout from '@/layouts/AppLayout.vue'
import { Plus } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()
const promotions = ref<Promotion[]>([])
const prefix = auth.isAdmin ? '/admin' : '/finance'

onMounted(async () => { promotions.value = await adminApi.getPromotions() })

async function toggleActive(p: Promotion) {
  try {
    const updated = await adminApi.updatePromotion(p.id, { is_active: !p.is_active })
    const idx = promotions.value.findIndex(x => x.id === p.id)
    if (idx !== -1) promotions.value[idx] = updated
  } catch (e: any) { ui.addToast(e.message, 'error') }
}

function fmt(v: number, type: string) {
  if (type === 'percent_off') return `${v}% off`
  if (type === 'fixed_off') return `$${v} off`
  if (type === 'threshold_fixed_off') return `$${v} off (threshold)`
  if (type === 'bogo_selected_workshops') return 'BOGO selected workshops'
  return String(type)
}
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Promotions</h1>
      <RouterLink :to="`${prefix}/promotions/new`" class="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
        <Plus class="h-4 w-4" /> New Promotion
      </RouterLink>
    </div>

    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Value</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Stack Group</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Valid</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Active</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in promotions" :key="p.id" class="border-t border-border hover:bg-muted/30 cursor-pointer"
            @click="router.push(`${prefix}/promotions/${p.id}/edit`)">
            <td class="px-4 py-3 font-medium text-foreground">{{ p.name }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ fmt(p.value, p.type) }}</td>
            <td class="px-4 py-3 font-mono text-xs text-muted-foreground">
              {{ p.is_exclusive ? '🔒 exclusive' : (p.stack_group ?? 'singleton') }}
            </td>
            <td class="px-4 py-3 text-xs text-muted-foreground">{{ p.valid_from?.slice(0, 10) }} → {{ p.valid_until?.slice(0, 10) }}</td>
            <td class="px-4 py-3">
              <button @click.stop="toggleActive(p)" :class="['text-xs font-medium px-2 py-0.5 rounded', p.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400']">
                {{ p.is_active ? 'Active' : 'Inactive' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
