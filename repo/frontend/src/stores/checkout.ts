import { defineStore } from 'pinia'
import { ref } from 'vue'
import { checkoutApi } from '@/api/endpoints/checkout'

export interface CartItem {
  session_id: string
  session_title: string
  unit_price: number
  quantity: number
}

export interface AppliedPromotion {
  promotion_id: string
  promotion_name: string
  discount_amount: number
  explanation: string
}

export interface Order {
  id: string
  learner_id: string
  status: 'pending' | 'paid' | 'cancelled' | 'refunded'
  subtotal: number
  discount_total: number
  total: number
  currency: string
  applied_promotions: AppliedPromotion[]
  items: CartItem[]
  created_at: string
  paid_at: string | null
  expires_at: string
}

export const useCheckoutStore = defineStore('checkout', () => {
  const order = ref<Order | null>(null)
  const loading = ref(false)

  async function createCart(items: { session_id: string; quantity: number }[]) {
    loading.value = true
    try {
      order.value = await checkoutApi.createCart(items)
      return order.value
    } finally {
      loading.value = false
    }
  }

  async function fetchOrder(id: string) {
    order.value = await checkoutApi.getOrder(id)
    return order.value
  }

  async function cancelOrder(id: string) {
    order.value = await checkoutApi.cancelOrder(id)
    return order.value
  }

  function clearCart() {
    order.value = null
  }

  return { order, loading, createCart, fetchOrder, cancelOrder, clearCart }
})
