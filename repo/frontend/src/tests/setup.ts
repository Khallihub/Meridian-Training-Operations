import { config } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

// Make Pinia available in all tests
beforeEach(() => {
  setActivePinia(createPinia())
})

// Mock browser APIs not available in jsdom
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
  })),
})

(globalThis as any).WebSocket = vi.fn().mockImplementation(() => ({
  send: vi.fn(), close: vi.fn(),
  onopen: null, onmessage: null, onerror: null, onclose: null,
  readyState: 1, CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3,
})) as any

// Mock crypto.randomUUID
Object.defineProperty(globalThis, 'crypto', {
  value: { randomUUID: () => '00000000-0000-0000-0000-000000000000' },
})
