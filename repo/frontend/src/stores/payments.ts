import { defineStore } from 'pinia'
import { ref } from 'vue'
import { paymentsApi } from '@/api/endpoints/payments'

export interface Payment {
  id: string
  order_id: string
  terminal_ref: string | null
  amount: number
  status: 'pending' | 'completed' | 'failed'
  callback_received_at: string | null
  signature_verified: boolean
}

export interface Refund {
  id: string
  payment_id: string
  order_id: string
  requested_by: string
  amount: number
  reason: string
  status: 'requested' | 'pending_review' | 'approved' | 'processing' | 'completed' | 'rejected' | 'failed' | 'canceled'
  created_at: string
  processed_at: string | null
}

export interface ReconciliationExport {
  id: string
  export_date: string
  file_path: string
  generated_at: string
  row_count: number
}

export const usePaymentsStore = defineStore('payments', () => {
  const currentPayment = ref<Payment | null>(null)
  const refunds = ref<Refund[]>([])
  const exports = ref<ReconciliationExport[]>([])
  const loading = ref(false)

  async function fetchPayment(orderId: string) {
    currentPayment.value = await paymentsApi.getPayment(orderId)
    return currentPayment.value
  }

  async function pollPayment(orderId: string, onPaid: () => void) {
    // Poll every 3s until status = completed or max 10 min
    const maxAttempts = 200
    let attempts = 0
    const interval = setInterval(async () => {
      attempts++
      try {
        const payment = await paymentsApi.getPayment(orderId)
        currentPayment.value = payment
        if (payment.status === 'completed') {
          clearInterval(interval)
          onPaid()
        }
      } catch { /* keep polling */ }
      if (attempts >= maxAttempts) clearInterval(interval)
    }, 3000)
    return () => clearInterval(interval)
  }

  async function submitRefund(payload: { order_id: string; amount: number; reason: string }) {
    return await paymentsApi.submitRefund(payload)
  }

  async function reviewRefund(id: string) {
    const updated = await paymentsApi.reviewRefund(id)
    _replaceRefund(updated)
    return updated
  }

  async function approveRefund(id: string) {
    const updated = await paymentsApi.approveRefund(id)
    _replaceRefund(updated)
    return updated
  }

  async function rejectRefund(id: string) {
    const updated = await paymentsApi.rejectRefund(id)
    _replaceRefund(updated)
    return updated
  }

  async function processRefund(id: string) {
    const updated = await paymentsApi.processRefund(id)
    _replaceRefund(updated)
    return updated
  }

  async function completeRefund(id: string) {
    const updated = await paymentsApi.completeRefund(id)
    _replaceRefund(updated)
    return updated
  }

  async function fetchRefunds(status?: string) {
    refunds.value = await paymentsApi.getRefunds(status)
  }

  async function triggerExport() {
    return await paymentsApi.triggerExport()
  }

  async function fetchExports() {
    exports.value = await paymentsApi.getExports()
  }

  function _replaceRefund(updated: Refund) {
    const idx = refunds.value.findIndex(r => r.id === updated.id)
    if (idx !== -1) refunds.value[idx] = updated
  }

  return {
    currentPayment, refunds, exports, loading,
    fetchPayment, pollPayment, submitRefund,
    reviewRefund, approveRefund, rejectRefund, processRefund, completeRefund,
    fetchRefunds, triggerExport, fetchExports,
  }
})
