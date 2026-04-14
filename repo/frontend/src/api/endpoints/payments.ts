import client from '../client'
import type { Payment, Refund, ReconciliationExport } from '@/stores/payments'

export const paymentsApi = {
  simulatePayment: async (orderId: string) => {
    const res = await client.post(`/api/v1/payments/${orderId}/simulate`)
    return res.data as Payment
  },
  getPayment: async (orderId: string) => {
    const res = await client.get(`/api/v1/payments/${orderId}`)
    return res.data as Payment
  },
  submitRefund: async (payload: { order_id: string; amount: number; reason: string }) => {
    const res = await client.post('/api/v1/refunds', payload)
    return res.data as Refund
  },
  reviewRefund: async (id: string) => {
    const res = await client.patch(`/api/v1/refunds/${id}/review`)
    return res.data as Refund
  },
  approveRefund: async (id: string) => {
    const res = await client.patch(`/api/v1/refunds/${id}/approve`)
    return res.data as Refund
  },
  rejectRefund: async (id: string) => {
    const res = await client.patch(`/api/v1/refunds/${id}/reject`)
    return res.data as Refund
  },
  processRefund: async (id: string) => {
    const res = await client.patch(`/api/v1/refunds/${id}/process`)
    return res.data as Refund
  },
  completeRefund: async (id: string) => {
    const res = await client.patch(`/api/v1/refunds/${id}/complete`)
    return res.data as Refund
  },
  getRefunds: async (status?: string) => {
    const res = await client.get('/api/v1/refunds', { params: status ? { status } : {} })
    return res.data as Refund[]
  },
  triggerExport: async () => {
    const res = await client.get('/api/v1/reconciliation/export')
    return res.data as ReconciliationExport
  },
  getExports: async () => {
    const res = await client.get('/api/v1/reconciliation/exports')
    return res.data as ReconciliationExport[]
  },
}
