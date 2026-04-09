import client from '../client'
import type { Order } from '@/stores/checkout'

export const checkoutApi = {
  createCart: async (items: { session_id: string; quantity: number }[]) => {
    const res = await client.post('/api/checkout/cart', { items })
    return res.data as Order
  },
  getOrder: async (id: string) => {
    const res = await client.get(`/api/orders/${id}`)
    return res.data as Order
  },
  getOrders: async (params?: Record<string, unknown>) => {
    const res = await client.get('/api/orders', { params })
    return { items: res.data.items as Order[], total: res.data.meta.total_count as number }
  },
  cancelOrder: async (id: string) => {
    const res = await client.patch(`/api/orders/${id}/cancel`)
    return res.data as Order
  },
}
