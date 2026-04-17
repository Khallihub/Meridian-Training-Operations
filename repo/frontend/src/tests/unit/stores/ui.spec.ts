import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUiStore } from '@/stores/ui'

describe('uiStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('initial theme defaults to light', () => {
    const store = useUiStore()
    expect(store.theme).toBe('light')
  })

  it('toggleTheme switches light to dark', () => {
    const store = useUiStore()
    store.toggleTheme()
    expect(store.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('toggleTheme switches dark back to light', () => {
    localStorage.setItem('theme', 'dark')
    setActivePinia(createPinia()) // reinit with dark theme in localStorage
    const store = useUiStore()
    expect(store.theme).toBe('dark')
    store.toggleTheme()
    expect(store.theme).toBe('light')
  })

  it('toggleSidebar flips collapsed state', () => {
    const store = useUiStore()
    expect(store.sidebarCollapsed).toBe(false)
    store.toggleSidebar()
    expect(store.sidebarCollapsed).toBe(true)
    expect(localStorage.getItem('sidebar')).toBe('true')
  })

  it('addToast adds a toast with generated id', () => {
    const store = useUiStore()
    store.addToast('Test message', 'success')
    expect(store.toasts).toHaveLength(1)
    expect(store.toasts[0].message).toBe('Test message')
    expect(store.toasts[0].type).toBe('success')
    expect(store.toasts[0].id).toBeTruthy()
  })

  it('addToast defaults to info type', () => {
    const store = useUiStore()
    store.addToast('Info toast')
    expect(store.toasts[0].type).toBe('info')
  })

  it('removeToast removes by id', () => {
    const store = useUiStore()
    // Directly push toasts to bypass setTimeout auto-removal
    const id1 = 'test-id-1'
    const id2 = 'test-id-2'
    store.toasts.push({ id: id1, message: 'Toast 1', type: 'info' })
    store.toasts.push({ id: id2, message: 'Toast 2', type: 'error' })
    expect(store.toasts).toHaveLength(2)
    store.removeToast(id1)
    expect(store.toasts).toHaveLength(1)
    expect(store.toasts[0].message).toBe('Toast 2')
  })

  it('multiple toggleSidebar roundtrips', () => {
    const store = useUiStore()
    store.toggleSidebar()
    store.toggleSidebar()
    expect(store.sidebarCollapsed).toBe(false)
    expect(localStorage.getItem('sidebar')).toBe('false')
  })
})
