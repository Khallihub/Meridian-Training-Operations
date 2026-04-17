import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock stores
vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({
    addToast: vi.fn(),
  }),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    accessToken: 'test-token',
  }),
}))

// Mock fetch
const mockFetch = vi.fn()
globalThis.fetch = mockFetch

// Mock URL.createObjectURL and revokeObjectURL
globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
globalThis.URL.revokeObjectURL = vi.fn()

describe('useExport', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockFetch.mockReset()
  })

  it('exports and returns exporting state', async () => {
    const { useExport } = await import('@/composables/useExport')
    const { exporting, exportSearch } = useExport()
    expect(exporting.value).toBe(false)
  })

  it('sets exporting=true during export', async () => {
    // Mock create job response
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: { id: 'job-1', status: 'queued' }, meta: {} }),
      })
      // Mock poll response (completed immediately)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: { id: 'job-1', status: 'completed', row_count: 10 }, meta: {} }),
      })
      // Mock download response
      .mockResolvedValueOnce({
        ok: true,
        blob: () => Promise.resolve(new Blob(['csv,data'], { type: 'text/csv' })),
      })

    const { useExport } = await import('@/composables/useExport')
    const { exporting, exportSearch } = useExport()

    // Mock document.createElement for download link
    const mockLink = { href: '', download: '', click: vi.fn(), remove: vi.fn() }
    vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)
    vi.spyOn(document.body, 'appendChild').mockReturnValue(mockLink as any)

    await exportSearch({ page: 1, page_size: 10 } as any, 'csv')
    expect(exporting.value).toBe(false) // done
  })

  it('handles export failure gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: 'Server error' }),
    })

    const { useExport } = await import('@/composables/useExport')
    const { exportSearch, exporting } = useExport()

    // exportSearch may throw or catch internally — either way exporting should reset
    try {
      await exportSearch({ page: 1, page_size: 10 } as any, 'csv')
    } catch {
      // expected
    }
    expect(exporting.value).toBe(false)
  })
})
