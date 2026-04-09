import client from '../client'
import type { Payment, Refund, ReconciliationExport } from '@/stores/payments'

export const paymentsApi = {
  simulatePayment: async (orderId: string) => {
    const res = await client.post(`/api/payments/${orderId}/simulate`)
    return res.data as Payment
  },
  getPayment: async (orderId: string) => {
    const res = await client.get(`/api/payments/${orderId}`)
    return res.data as Payment
  },
  submitRefund: async (payload: { order_id: string; amount: number; reason: string }) => {
    const res = await client.post('/api/refunds', payload)
    return res.data as Refund
  },
  approveRefund: async (id: string) => {
    const res = await client.patch(`/api/refunds/${id}/approve`)
    return res.data as Refund
  },
  completeRefund: async (id: string) => {
    const res = await client.patch(`/api/refunds/${id}/complete`)
    return res.data as Refund
  },
  getRefunds: async (status?: string) => {
    const res = await client.get('/api/refunds', { params: status ? { status } : {} })
    return res.data as Refund[]
  },
  triggerExport: async () => {
    const res = await client.get('/api/reconciliation/export')
    return res.data as ReconciliationExport
  },
  getExports: async () => {
    const res = await client.get('/api/reconciliation/exports')
    return res.data as ReconciliationExport[]
  },
}
