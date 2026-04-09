import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/endpoints/auth'

export interface User {
  id: string
  username: string
  role: 'admin' | 'instructor' | 'learner' | 'finance' | 'dataops'
  tz: string
}

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000  // must mirror server INACTIVITY_TIMEOUT_MINUTES

function recordActivity() {
  localStorage.setItem('last_active', String(Date.now()))
}

function isClientSideInactive(): boolean {
  const raw = localStorage.getItem('last_active')
  if (!raw) return true  // no record → treat as inactive (mirrors server behaviour)
  return Date.now() - Number(raw) > INACTIVITY_TIMEOUT_MS
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)
  const role = computed(() => user.value?.role)
  const isAdmin = computed(() => role.value === 'admin')
  const isInstructor = computed(() => role.value === 'instructor')
  const isLearner = computed(() => role.value === 'learner')
  const isFinance = computed(() => role.value === 'finance')
  const isDataOps = computed(() => role.value === 'dataops')

  function decodeJwt(token: string): { sub: string; role: User['role']; exp: number } {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload))
  }

  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.login(username, password)
      accessToken.value = data.access_token
      const claims = decodeJwt(data.access_token)
      user.value = {
        id: claims.sub,
        username,
        role: claims.role,
        tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
      }
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('auth_user', JSON.stringify(user.value))
      recordActivity()
    } finally {
      loading.value = false
    }
  }

  async function refresh() {
    const rt = localStorage.getItem('refresh_token')
    if (!rt) throw new Error('No refresh token')
    const data = await authApi.refresh(rt)
    accessToken.value = data.access_token
    localStorage.setItem('refresh_token', data.refresh_token)
    recordActivity()
    // Restore user info, updating role from the fresh JWT
    const claims = decodeJwt(data.access_token)
    const stored = localStorage.getItem('auth_user')
    if (stored) {
      user.value = { ...JSON.parse(stored), role: claims.role }
    } else {
      user.value = { id: claims.sub, username: claims.sub, role: claims.role, tz: Intl.DateTimeFormat().resolvedOptions().timeZone }
    }
    return data.access_token
  }

  async function logout() {
    try { await authApi.logout() } catch { /* ignore */ }
    accessToken.value = null
    user.value = null
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('last_active')
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    await authApi.changePassword(currentPassword, newPassword)
  }

  // Restore session on app load from refresh token.
  // Skip the network call entirely if the client-side inactivity window has elapsed —
  // the server would reject it anyway, and this avoids a spurious round-trip.
  async function restoreSession() {
    const rt = localStorage.getItem('refresh_token')
    if (!rt) return
    if (isClientSideInactive()) {
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('auth_user')
      localStorage.removeItem('last_active')
      return
    }
    try {
      await refresh()
    } catch {
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('last_active')
    }
  }

  return {
    user, accessToken, loading, error,
    isAuthenticated, role, isAdmin, isInstructor, isLearner, isFinance, isDataOps,
    login, refresh, logout, changePassword, restoreSession, recordActivity,
  }
})
