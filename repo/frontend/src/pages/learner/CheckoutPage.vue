<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCheckoutStore } from '@/stores/checkout'
import AppLayout from '@/layouts/AppLayout.vue'
import DiscountTraceability from '@/components/checkout/DiscountTraceability.vue'

const router = useRouter()
const checkout = useCheckoutStore()

onMounted(() => {
  if (!checkout.order) {
    router.replace('/learner/sessions')
  }
})

function handleProceed() {
  const id = checkout.order!.id
  checkout.clearCart()
  router.push(`/learner/orders/${id}`)
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}
</script>

<template>
  <AppLayout>
    <div class="max-w-2xl mx-auto">
      <h1 class="text-xl font-semibold text-foreground mb-6">Checkout</h1>

      <div v-if="!checkout.order" class="text-center py-16 text-muted-foreground">
        Your cart is empty. <RouterLink to="/learner/sessions" class="text-primary hover:underline">Browse sessions</RouterLink>
      </div>

      <template v-else>
        <!-- Cart items -->
        <div class="bg-card border border-border rounded-lg p-5 mb-4">
          <h2 class="font-medium text-foreground mb-3">Sessions</h2>
          <div v-for="item in checkout.order.items" :key="item.session_id" class="flex items-center justify-between py-2 border-b border-border last:border-0">
            <div>
              <p class="text-sm font-medium text-foreground">{{ item.session_title }}</p>
              <p class="text-xs text-muted-foreground">Qty: {{ item.quantity }}</p>
            </div>
            <span class="text-sm font-medium">{{ fmt(item.unit_price * item.quantity) }}</span>
          </div>
        </div>

        <!-- Order summary with discount traceability -->
        <div class="bg-card border border-border rounded-lg p-5 mb-6">
          <h2 class="font-medium text-foreground mb-3">Order Summary</h2>
          <DiscountTraceability
            :promotions="checkout.order.applied_promotions"
            :subtotal="checkout.order.subtotal"
            :discount-total="checkout.order.discount_total"
            :total="checkout.order.total"
          />
        </div>

        <!-- Proceed -->
        <button
          @click="handleProceed"
          class="w-full py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 flex items-center justify-center gap-2"
        >
          Proceed to Payment Terminal
        </button>
      </template>
    </div>
  </AppLayout>
</template>
