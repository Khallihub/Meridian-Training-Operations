import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory, RouterLink } from 'vue-router'

// Minimal router for RouterLink resolution
const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: { template: '<div>Home</div>' } }],
})

describe('ForbiddenPage (403)', () => {
  it('renders 403 and access denied message', async () => {
    const Comp = (await import('@/pages/ForbiddenPage.vue')).default
    const wrapper = mount(Comp, {
      global: { plugins: [router], stubs: { RouterLink: true } },
    })
    expect(wrapper.text()).toContain('403')
    expect(wrapper.text().toLowerCase()).toContain('denied')
  })

  it('contains link to home', async () => {
    const Comp = (await import('@/pages/ForbiddenPage.vue')).default
    const wrapper = mount(Comp, {
      global: { plugins: [router], stubs: { RouterLink: true } },
    })
    expect(wrapper.findComponent({ name: 'RouterLink' }).exists() || wrapper.find('a').exists()).toBe(true)
  })
})

describe('NotFoundPage (404)', () => {
  it('renders 404 and not found message', async () => {
    const Comp = (await import('@/pages/NotFoundPage.vue')).default
    const wrapper = mount(Comp, {
      global: { plugins: [router], stubs: { RouterLink: true } },
    })
    expect(wrapper.text()).toContain('404')
    expect(wrapper.text().toLowerCase()).toContain('not found')
  })

  it('contains link to home', async () => {
    const Comp = (await import('@/pages/NotFoundPage.vue')).default
    const wrapper = mount(Comp, {
      global: { plugins: [router], stubs: { RouterLink: true } },
    })
    expect(wrapper.findComponent({ name: 'RouterLink' }).exists() || wrapper.find('a').exists()).toBe(true)
  })
})
