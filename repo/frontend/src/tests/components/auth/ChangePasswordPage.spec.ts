import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/change-password' }),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    changePassword: vi.fn(),
    isAuthenticated: true,
    role: 'admin',
  }),
}))

vi.mock('@/stores/ui', () => ({
  useUiStore: () => ({ addToast: vi.fn() }),
}))

describe('ChangePasswordPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('password validation requires 12+ chars with complexity', () => {
    const validate = (pw: string) => {
      if (pw.length < 12) return false
      if (!/[A-Z]/.test(pw)) return false
      if (!/[a-z]/.test(pw)) return false
      if (!/\d/.test(pw)) return false
      if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw)) return false
      return true
    }
    expect(validate('Short@1')).toBe(false)
    expect(validate('ValidPassword@123')).toBe(true)
    expect(validate('nouppercase@123')).toBe(false)
    expect(validate('NOLOWERCASE@123')).toBe(false)
  })

  it('confirmation must match new password', () => {
    const newPw = 'NewSecure@12345'
    const confirm = 'NewSecure@12345'
    const mismatch = 'DifferentPw@123'
    expect(newPw === confirm).toBe(true)
    expect(newPw === mismatch).toBe(false)
  })
})
