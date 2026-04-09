import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DiscountTraceability from '@/components/checkout/DiscountTraceability.vue'

const mockPromotions = [
  {
    promotion_id: 'p1',
    promotion_name: 'Buy-One-Get-One',
    promotion_type: 'bogo',
    discount_amount: 50,
    explanation: "Applied 'Buy-One-Get-One' because you have 2 workshops",
  },
  {
    promotion_id: 'p2',
    promotion_name: '$5 bundle',
    promotion_type: 'fixed_off',
    discount_amount: 5,
    explanation: "Applied '$5 bundle' from bundle-group — best option selected",
  },
]

describe('DiscountTraceability — correction #1', () => {
  it('renders promotion names', () => {
    const wrapper = mount(DiscountTraceability, {
      props: { promotions: mockPromotions, subtotal: 100, discountTotal: 55, total: 45 },
    })
    expect(wrapper.text()).toContain('Buy-One-Get-One')
    expect(wrapper.text()).toContain('$5 bundle')
  })

  it('renders WHY explanation text — correction #1', () => {
    const wrapper = mount(DiscountTraceability, {
      props: { promotions: mockPromotions, subtotal: 100, discountTotal: 55, total: 45 },
    })
    expect(wrapper.text()).toContain('because you have 2 workshops')
    expect(wrapper.text()).toContain('best option selected')
  })

  it('renders discount amounts', () => {
    const wrapper = mount(DiscountTraceability, {
      props: { promotions: mockPromotions, subtotal: 100, discountTotal: 55, total: 45 },
    })
    expect(wrapper.text()).toContain('$50')
    expect(wrapper.text()).toContain('$5')
  })

  it('renders totals section', () => {
    const wrapper = mount(DiscountTraceability, {
      props: { promotions: mockPromotions, subtotal: 100, discountTotal: 55, total: 45 },
    })
    expect(wrapper.text()).toContain('$100')  // subtotal
    expect(wrapper.text()).toContain('$45')   // total
  })

  it('shows "No promotions" when empty', () => {
    const wrapper = mount(DiscountTraceability, {
      props: { promotions: [], subtotal: 100, discountTotal: 0, total: 100 },
    })
    expect(wrapper.text()).toContain('No promotions applied')
  })
})
