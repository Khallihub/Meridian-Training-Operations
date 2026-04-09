<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCheckoutStore } from '@/stores/checkout'
import { useUiStore } from '@/stores/ui'
import { paymentsApi } from '@/api/endpoints/payments'
import { formatInTimeZone } from 'date-fns-tz'
import { parseISO } from 'date-fns'
import AppLayout from '@/layouts/AppLayout.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import DiscountTraceability from '@/components/checkout/DiscountTraceability.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import { Printer } from 'lucide-vue-next'

const route = useRoute()
const checkout = useCheckoutStore()
const ui = useUiStore()

const isSimulating = ref(false)
async function handleSimulate() {
  isSimulating.value = true
  try {
    await paymentsApi.simulatePayment(orderId)
    // polling will pick up the status change within 3 s
  } catch (e: any) {
    ui.addToast(e.message ?? 'Simulation failed', 'error')
  } finally {
    isSimulating.value = false
  }
}

const orderId = route.params.id as string
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone

const paymentStatus = ref<'pending' | 'completed' | 'failed' | null>(null)
const waitingForTerminal = ref(false)
let pollInterval: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await checkout.fetchOrder(orderId)

  const o = checkout.order
  if (!o) return

  if (o.status === 'pending') {
    waitingForTerminal.value = true
    let attempts = 0
    pollInterval = setInterval(async () => {
      attempts++
      try {
        await checkout.fetchOrder(orderId)
        if (checkout.order?.status === 'paid') {
          clearInterval(pollInterval!)
          waitingForTerminal.value = false
          paymentStatus.value = 'completed'
          ui.addToast('Payment received!', 'success')
        }
      } catch { /* keep polling */ }
      if (attempts >= 200) clearInterval(pollInterval!)
    }, 3000)
  } else if (o.status === 'paid') {
    paymentStatus.value = 'completed'
  } else {
    paymentStatus.value = o.status as any
  }
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

const order = computed(() => checkout.order)

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: order.value?.currency ?? 'USD' }).format(n)
}

function fmtDate(dt: string) {
  return formatInTimeZone(parseISO(dt), tz, 'MMM d, yyyy h:mm a')
}

function printPage() {
  window.print()
}
</script>

<template>
  <AppLayout>
    <div class="max-w-2xl mx-auto">
      <!-- Print button -->
      <div class="flex items-center justify-between mb-6 no-print">
        <h1 class="text-xl font-semibold text-foreground">Order Receipt</h1>
        <button @click="printPage()" class="flex items-center gap-2 px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">
          <Printer class="h-4 w-4" /> Print
        </button>
      </div>

      <LoadingSpinner v-if="!order" class="py-16" />

      <template v-else>
        <!-- Waiting for terminal state -->
        <div v-if="waitingForTerminal" class="mb-4 flex items-center gap-3 p-4 rounded-lg bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200">
          <div class="h-4 w-4 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin shrink-0" />
          <div>
            <p class="text-sm font-medium">Waiting for payment terminal…</p>
            <p class="text-xs mt-0.5">Please complete payment on the LAN terminal. This page will update automatically.</p>
          </div>
        </div>

        <!-- Terminal simulator -->
        <div v-if="waitingForTerminal" class="mb-4 p-4 rounded-lg border border-dashed border-border bg-muted/20 no-print">
          <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Terminal Simulator</p>
          <p class="text-xs text-muted-foreground mb-3">
            No physical terminal? Click below to generate a signed payment callback for order
            <span class="font-mono">{{ orderId.slice(0, 8) }}…</span>
            totalling <strong>{{ order ? fmt(order.total) : '…' }}</strong>.
          </p>
          <button
            @click="handleSimulate"
            :disabled="isSimulating"
            class="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
          >
            <div v-if="isSimulating" class="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            {{ isSimulating ? 'Processing…' : 'Simulate Payment' }}
          </button>
        </div>

        <!-- Payment confirmed banner -->
        <div v-else-if="paymentStatus === 'completed'" class="mb-4 flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-200">
          <svg class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <p class="text-sm font-medium">Payment confirmed</p>
        </div>

        <!-- Order card -->
        <div class="bg-card border border-border rounded-lg p-6 print-only-visible">
          <!-- Order header -->
          <div class="flex items-start justify-between mb-5 pb-5 border-b border-border">
            <div>
              <p class="text-xs text-muted-foreground">Order ID</p>
              <p class="font-mono text-sm">{{ order.id }}</p>
            </div>
            <div class="text-right">
              <StatusBadge :status="order.status" />
              <p class="text-xs text-muted-foreground mt-1">{{ fmtDate(order.created_at) }}</p>
            </div>
          </div>

          <!-- Items -->
          <div class="space-y-2 mb-5">
            <h3 class="text-sm font-medium text-foreground">Sessions</h3>
            <div v-for="item in order.items" :key="item.session_id" class="flex justify-between text-sm">
              <span>{{ item.session_title }}</span>
              <span class="font-medium">{{ fmt(item.unit_price * item.quantity) }}</span>
            </div>
          </div>

          <!-- Discount traceability — correction #1 on receipt screen -->
          <DiscountTraceability
            :promotions="order.applied_promotions ?? []"
            :subtotal="order.subtotal"
            :discount-total="order.discount_total"
            :total="order.total"
            :currency="order.currency"
          />

          <div v-if="order.paid_at" class="mt-4 pt-4 border-t border-border text-xs text-muted-foreground">
            Paid on {{ fmtDate(order.paid_at) }}
          </div>
        </div>
      </template>
    </div>
  </AppLayout>
</template>
