<script setup lang="ts">
import type { AppliedPromotion } from '@/stores/checkout'
import { Tag } from 'lucide-vue-next'

defineProps<{
  promotions: AppliedPromotion[]
  subtotal: number
  discountTotal: number
  total: number
  currency?: string
}>()

function fmt(n: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(n)
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <!-- Applied discount explanations — correction #1 -->
    <div v-if="promotions.length > 0" class="space-y-2">
      <h3 class="text-sm font-medium text-foreground">Applied Discounts</h3>
      <div
        v-for="promo in promotions"
        :key="promo.promotion_id"
        class="flex items-start gap-3 p-3 rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800"
      >
        <Tag class="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-green-800 dark:text-green-200">{{ promo.promotion_name }}</span>
            <span class="text-sm font-semibold text-green-700 dark:text-green-300 shrink-0">
              −{{ fmt(promo.discount_amount, currency) }}
            </span>
          </div>
          <!-- "Why" explanation — the traceable part -->
          <p class="text-xs text-green-700 dark:text-green-400 mt-0.5">{{ promo.explanation }}</p>
        </div>
      </div>
    </div>

    <div v-else class="text-sm text-muted-foreground">No promotions applied.</div>

    <!-- Order totals -->
    <div class="border-t border-border pt-3 space-y-1.5 text-sm">
      <div class="flex justify-between text-muted-foreground">
        <span>Subtotal</span>
        <span>{{ fmt(subtotal, currency) }}</span>
      </div>
      <div v-if="discountTotal > 0" class="flex justify-between text-green-600 dark:text-green-400">
        <span>Total savings</span>
        <span>−{{ fmt(discountTotal, currency) }}</span>
      </div>
      <div class="flex justify-between font-semibold text-foreground text-base pt-1 border-t border-border">
        <span>Total</span>
        <span>{{ fmt(total, currency) }}</span>
      </div>
    </div>
  </div>
</template>
