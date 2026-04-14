import { ref, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

export interface RoomState {
  session_status: string
  enrolled_count: number
  checked_in_count: number
}

export interface RoomEvent {
  type: string
  payload: Record<string, unknown>
  timestamp: Date
}

export function useWebSocket(sessionId: string) {
  const auth = useAuthStore()
  const roomState = ref<RoomState | null>(null)
  const events = ref<RoomEvent[]>([])
  const connectionStatus = ref<'connecting' | 'connected' | 'disconnected' | 'error'>('connecting')

  const wsRef = ref<WebSocket | null>(null)
  let ws: WebSocket | null = null
  let retryDelay = 1000
  let retryTimeout: ReturnType<typeof setTimeout> | null = null
  let destroyed = false

  // Direct synchronous message handlers — called for every incoming message
  // before any Vue reactivity update. Used by LiveRoomModal for WebRTC signaling
  // so that messages are never lost to batching or async watcher concurrency.
  const _rawHandlers: Array<(msg: Record<string, unknown>) => void> = []

  function addMessageHandler(handler: (msg: Record<string, unknown>) => void): () => void {
    _rawHandlers.push(handler)
    return () => {
      const idx = _rawHandlers.indexOf(handler)
      if (idx >= 0) _rawHandlers.splice(idx, 1)
    }
  }

  function connect() {
    if (destroyed) return
    const token = auth.accessToken
    if (!token) { connectionStatus.value = 'error'; return }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/api/ws/sessions/${sessionId}/room?token=${token}`

    ws = new WebSocket(url)
    wsRef.value = ws
    connectionStatus.value = 'connecting'

    ws.onopen = () => {
      connectionStatus.value = 'connected'
      retryDelay = 1000
    }

    ws.onmessage = (evt) => {
      let msg: Record<string, unknown>
      try { msg = JSON.parse(evt.data) } catch { return }

      const type = msg.type as string

      // 1. Notify direct handlers synchronously (WebRTC signaling path)
      for (const h of _rawHandlers) {
        try { h(msg) } catch {}
      }

      // 2. Update the reactive events list (activity feed)
      const next = [{ type, payload: msg, timestamp: new Date() }, ...events.value]
      events.value = next.length > 100 ? next.slice(0, 100) : next

      if (type === 'room_state') {
        roomState.value = {
          session_status: msg.session_status as string,
          enrolled_count: msg.enrolled_count as number,
          checked_in_count: msg.checked_in_count as number,
        }
      } else if (type === 'session_status_changed') {
        if (roomState.value) roomState.value.session_status = msg.status as string
      } else if (type === 'attendee_joined') {
        if (roomState.value) roomState.value.checked_in_count++
      } else if (type === 'attendee_left') {
        if (roomState.value && roomState.value.checked_in_count > 0) roomState.value.checked_in_count--
      } else if (type === 'roster_update') {
        if (roomState.value) roomState.value.enrolled_count = msg.enrolled_count as number
      }
    }

    ws.onerror = () => { connectionStatus.value = 'error' }

    ws.onclose = (evt) => {
      connectionStatus.value = 'disconnected'
      // Do not retry on auth failures (4001 = unauthorized, 4003 = forbidden) —
      // retrying won't help without a new token and will just spam the server.
      const authFailure = evt.code === 4001 || evt.code === 4003
      if (!destroyed && evt.code !== 1000 && !authFailure) {
        // Exponential backoff, max 30s
        retryTimeout = setTimeout(() => { retryDelay = Math.min(retryDelay * 2, 30000); connect() }, retryDelay)
      }
    }
  }

  function disconnect() {
    destroyed = true
    if (retryTimeout) clearTimeout(retryTimeout)
    ws?.close(1000, 'component unmounted')
  }

  connect()
  onUnmounted(disconnect)

  return { roomState, events, connectionStatus, disconnect, ws: wsRef, addMessageHandler }
}
