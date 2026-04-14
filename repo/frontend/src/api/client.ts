import axios, { type AxiosRequestConfig } from 'axios'

// Lazy import helper to avoid circular dependency at module load time
let _useAuthStore: typeof import('@/stores/auth')['useAuthStore'] | null = null
async function getAuthStore() {
  if (!_useAuthStore) {
    const mod = await import('@/stores/auth')
    _useAuthStore = mod.useAuthStore
  }
  return _useAuthStore()
}
function getAuthStoreSync() {
  if (!_useAuthStore) return null
  return _useAuthStore()
}

const client = axios.create({
  baseURL: '/',
  headers: { 'Content-Type': 'application/json' },
})

// Attach Bearer token from auth store on every request
client.interceptors.request.use(async config => {
  const auth = await getAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  // Let the browser set Content-Type (with boundary) for multipart uploads
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

// Queue for requests waiting on token refresh
let refreshing = false
let waitQueue: Array<{ resolve: (token: string) => void; reject: (e: unknown) => void }> = []

function processQueue(error: unknown, token: string | null) {
  waitQueue.forEach(p => error ? p.reject(error) : p.resolve(token!))
  waitQueue = []
}

client.interceptors.response.use(
  res => {
    // Slide the client-side inactivity window on every successful authenticated response
    const auth = getAuthStoreSync()
    if (auth?.accessToken) auth.recordActivity()

    // Unwrap the standard PRD response envelope: { data, meta, error }
    // Only unwrap responses from /api/v1/* that have the envelope shape
    if (
      res.data &&
      typeof res.data === 'object' &&
      'data' in res.data &&
      'meta' in res.data &&
      'error' in res.data
    ) {
      res.data = res.data.data
    }

    return res
  },
  async error => {
    const original: AxiosRequestConfig & { _retry?: boolean } = error.config
    const status = error.response?.status

    if (status === 401 && !original._retry && !original.url?.includes('/api/v1/auth/refresh') && !original.url?.includes('/api/v1/auth/login')) {
      if (refreshing) {
        return new Promise((resolve, reject) => {
          waitQueue.push({
            resolve: token => {
              original.headers = { ...original.headers, Authorization: `Bearer ${token}` }
              resolve(client(original))
            },
            reject,
          })
        })
      }

      original._retry = true
      refreshing = true

      try {
        const auth = await getAuthStore()
        const newToken = await auth.refresh()
        processQueue(null, newToken)
        original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` }
        return client(original)
      } catch (refreshError) {
        processQueue(refreshError, null)
        const auth = await getAuthStore()
        await auth.logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        refreshing = false
      }
    }

    // Normalize error shape — FastAPI validation errors return detail as an array of objects
    const rawDetail = error.response?.data?.detail
    const message = Array.isArray(rawDetail)
      ? rawDetail.map((e: any) => e.msg ?? String(e)).join(', ')
      : rawDetail ?? error.response?.data?.message ?? error.message
    const normalized = Object.assign(new Error(message), {
      statusCode: status,
      errors: error.response?.data?.errors,
    })
    return Promise.reject(normalized)
  }
)

export default client
