import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import SavedSearchSidebar from '@/components/search/SavedSearchSidebar.vue'
import { useSearchStore } from '@/stores/search'

vi.mock('@/api/endpoints/search', () => ({
  searchApi: { getSaved: vi.fn().mockResolvedValue([]), saveSearch: vi.fn(), deleteSearch: vi.fn(), search: vi.fn() },
}))

describe('SavedSearchSidebar — correction #2', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders saved searches from store', async () => {
    const store = useSearchStore()
    store.savedSearches = [
      { id: '1', name: 'Downtown Confirmed', filters_json: { enrollment_status: 'confirmed' }, created_at: '' },
      { id: '2', name: 'Pending Refunds View', filters_json: { enrollment_status: 'pending' }, created_at: '' },
    ]
    const wrapper = mount(SavedSearchSidebar)
    expect(wrapper.text()).toContain('Downtown Confirmed')
    expect(wrapper.text()).toContain('Pending Refunds View')
  })

  it('shows count against max 20', async () => {
    const store = useSearchStore()
    store.savedSearches = Array.from({ length: 15 }, (_, i) => ({ id: `${i}`, name: `Search ${i}`, filters_json: {}, created_at: '' }))
    const wrapper = mount(SavedSearchSidebar)
    expect(wrapper.text()).toContain('15/20')
  })

  it('emits load event with filters when clicked', async () => {
    const store = useSearchStore()
    store.savedSearches = [{ id: '1', name: 'My Search', filters_json: { enrollment_status: 'confirmed', site_id: 'site-1' }, created_at: '' }]
    const wrapper = mount(SavedSearchSidebar)
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('load')).toBeTruthy()
    expect(wrapper.emitted('load')![0][0]).toMatchObject({ enrollment_status: 'confirmed', site_id: 'site-1' })
  })
})
