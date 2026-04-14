<script setup lang="ts">
import { ref, computed, onUnmounted, nextTick, reactive } from 'vue'
import { X, Wifi, WifiOff, Mic, MicOff, Video, VideoOff, Monitor, Circle, StopCircle } from 'lucide-vue-next'
import type { Session } from '@/stores/sessions'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAuthStore } from '@/stores/auth'
import { sessionsApi } from '@/api/endpoints/sessions'
import StatusBadge from '@/components/shared/StatusBadge.vue'

const props = defineProps<{ session: Session }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const auth = useAuthStore()
const isInstructor = computed(() => auth.isInstructor || auth.isAdmin)

const { roomState, events, connectionStatus, ws: wsRef, addMessageHandler } = useWebSocket(props.session.id)

// ── Media state ───────────────────────────────────────────────────────────────
const localVideo = ref<HTMLVideoElement | null>(null)
const remoteVideo = ref<HTMLVideoElement | null>(null)
const micOn = ref(false)
const camOn = ref(false)
const screenSharing = ref(false)
const recording = ref(false)
const uploadState = reactive({ uploading: false, done: false, error: '' })
const hasStream = computed(() => camOn.value || screenSharing.value)
// Reactive flag set when the remote stream arrives — used to hide the "Waiting" overlay.
// Cannot use remoteVideo?.srcObject directly because DOM property mutations are not reactive.
const hasRemoteStream = ref(false)

// localStream is always a real MediaStream — tracks are added/removed from it
const localStream = new MediaStream()

let mediaRecorder: MediaRecorder | null = null
let recordedChunks: BlobPart[] = []
let peerConnection: RTCPeerConnection | null = null

// ── Activity feed ─────────────────────────────────────────────────────────────
const eventLabels: Record<string, (p: Record<string, unknown>) => string> = {
  attendee_joined:       (p) => `${p.learner_name ?? 'A learner'} joined`,
  attendee_left:         (p) => `${p.learner_name ?? 'A learner'} left`,
  session_status_changed:(p) => `Session is now ${String(p.status).toUpperCase()}`,
  roster_update:         (p) => `Enrollment updated: ${p.enrolled_count}`,
  room_state:            ()  => 'Connected to live room',
  peer_joined:           (p) => p.role === 'learner' ? 'A learner joined the room' : '',
  peer_left:             (p) => p.role === 'learner' ? 'A learner left the room' : '',
  webrtc_offer:          ()  => 'Stream available — connecting…',
  webrtc_answer:         ()  => 'Participant connected',
  webrtc_ice:            ()  => '',
  room_peers:            ()  => '',
}
function eventLabel(evt: { type: string; payload: Record<string, unknown> }) {
  return eventLabels[evt.type]?.(evt.payload) ?? evt.type
}
const isCompleted = computed(() =>
  roomState.value?.session_status === 'ended' || roomState.value?.session_status === 'canceled'
)

// ── WebRTC ────────────────────────────────────────────────────────────────────
// Instructor maintains one RTCPeerConnection per learner
const peerConnections = new Map<string, RTCPeerConnection>()
// All known learner IDs in the room — tracked even before streaming starts
const knownLearnerIds = new Set<string>()
// ICE candidate buffer: holds candidates that arrive before setRemoteDescription
// completes; flushed immediately after remote description is set.
const iceCandidateQueue = new Map<string, RTCIceCandidateInit[]>()

// ── Sequential signaling queue ────────────────────────────────────────────────
// WebRTC setup involves async operations (setRemoteDescription, createAnswer, …).
// Using a Vue watch callback is unsafe because Vue fires async watchers
// concurrently — a webrtc_ice message can run while webrtc_offer is still
// awaiting setRemoteDescription, causing addIceCandidate to fail silently.
// Solution: every incoming WebSocket message is pushed onto a plain array queue
// and drained one-at-a-time by a single async loop.
const _sigQueue: Record<string, unknown>[] = []
let _sigDraining = false

function _enqueue(msg: Record<string, unknown>) {
  _sigQueue.push(msg)
  if (!_sigDraining) _drainQueue()
}

async function _drainQueue() {
  _sigDraining = true
  while (_sigQueue.length > 0) {
    const msg = _sigQueue.shift()!
    try {
      await _handleSignal(msg)
    } catch (err) {
      // A bad message (e.g. an SDP answer for a now-replaced peer connection)
      // must not kill the queue permanently. Log and continue so subsequent
      // signals (ICE candidates, new offers) are still processed.
      console.error('[LiveRoom] _handleSignal error, dropping message:', (msg as any).type, err)
    }
  }
  _sigDraining = false
}

// Register the direct (synchronous) handler so every WS message is enqueued
// before Vue's reactivity system has a chance to batch or skip anything.
const _removeHandler = addMessageHandler(_enqueue)

const _role = computed(() => isInstructor.value ? 'INSTRUCTOR' : 'LEARNER')

function sendWs(msg: object) {
  const state = wsRef.value?.readyState
  if (state === WebSocket.OPEN) {
    wsRef.value!.send(JSON.stringify(msg))
  } else {
    console.warn(`[LiveRoom][${_role.value}] sendWs DROPPED (ws state=${state})`, msg)
  }
}

function createPeerConnectionFor(peerId: string): RTCPeerConnection {
  const existing = peerConnections.get(peerId)
  if (existing) {
    console.log(`[LiveRoom][${_role.value}] closing old PC for peer=${peerId}`)
    existing.close(); peerConnections.delete(peerId)
  }

  const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] })
  console.log(`[LiveRoom][${_role.value}] created PC for peer=${peerId}`)

  pc.onicecandidate = (e) => {
    if (e.candidate) {
      console.log(`[LiveRoom][${_role.value}] sending ICE to peer=${peerId}`)
      sendWs({ type: 'webrtc_ice', candidate: e.candidate, target_user_id: peerId })
    } else {
      console.log(`[LiveRoom][${_role.value}] ICE gathering complete for peer=${peerId}`)
    }
  }

  pc.ontrack = (e) => {
    console.log(`[LiveRoom][${_role.value}] ontrack fired, streams=${e.streams.length}, tracks=${e.track.kind}, isInstructor=${isInstructor.value}`)
    if (!isInstructor.value && e.streams[0]) {
      nextTick(() => {
        if (remoteVideo.value) {
          remoteVideo.value.srcObject = e.streams[0]
          hasRemoteStream.value = true
          remoteVideo.value.play().catch((err) => {
            console.warn(`[LiveRoom][LEARNER] play() rejected:`, err)
          })
          console.log(`[LiveRoom][LEARNER] stream attached, hasRemoteStream=true`)
        } else {
          console.error(`[LiveRoom][LEARNER] ontrack fired but remoteVideo ref is null!`)
        }
      })
    }
  }

  pc.onconnectionstatechange = () => {
    console.log(`[LiveRoom][${_role.value}] connectionState=${pc.connectionState} peer=${peerId}`)
    if (!isInstructor.value &&
        (pc.connectionState === 'disconnected' ||
         pc.connectionState === 'failed' ||
         pc.connectionState === 'closed')) {
      hasRemoteStream.value = false
      if (remoteVideo.value) remoteVideo.value.srcObject = null
    }
  }

  pc.oniceconnectionstatechange = () => {
    console.log(`[LiveRoom][${_role.value}] iceConnectionState=${pc.iceConnectionState} peer=${peerId}`)
  }

  peerConnections.set(peerId, pc)
  return pc
}

// Instructor: send offer to a specific learner, adding all current tracks
async function offerToLearner(learnerId: string) {
  if (!isInstructor.value) { console.warn('[LiveRoom] offerToLearner called but not instructor'); return }
  if (localStream.getTracks().length === 0) { console.warn('[LiveRoom] offerToLearner: no local tracks'); return }
  console.log(`[LiveRoom][INSTRUCTOR] offerToLearner learnerId=${learnerId}, tracks=${localStream.getTracks().length}`)
  const pc = createPeerConnectionFor(learnerId)
  localStream.getTracks().forEach(t => pc.addTrack(t, localStream))
  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)
  console.log(`[LiveRoom][INSTRUCTOR] offer created and set, sending to learner=${learnerId}`)
  sendWs({ type: 'webrtc_offer', sdp: offer, target_user_id: learnerId })
}

async function _handleSignal(msg: Record<string, unknown>) {
  const type = msg.type as string
  if (type !== 'webrtc_ice') {
    console.log(`[LiveRoom][${_role.value}] _handleSignal type=${type}`, msg)
  }

  if (type === 'peer_joined' && isInstructor.value && msg.role !== 'instructor') {
    const learnerId = msg.user_id as string
    knownLearnerIds.add(learnerId)
    console.log(`[LiveRoom][INSTRUCTOR] peer_joined learnerId=${learnerId}, streaming=${localStream.getTracks().length > 0}`)
    if (localStream.getTracks().length > 0) {
      // Only send a new offer if there is no healthy peer connection already.
      // The learner may also send a webrtc_request (from room_peers) which
      // would trigger a second offer and cause a double-offer race.
      const existing = peerConnections.get(learnerId)
      const isHealthy = !!existing &&
        existing.connectionState !== 'failed' &&
        existing.connectionState !== 'closed' &&
        existing.connectionState !== 'disconnected'
      if (!isHealthy) {
        await offerToLearner(learnerId)
      } else {
        console.log(`[LiveRoom][INSTRUCTOR] peer_joined: skipping offer, healthy PC exists for ${learnerId}`)
      }
    }

  } else if (type === 'peer_joined' && !isInstructor.value && msg.role !== 'learner') {
    // Instructor (or admin) joined the room after us. Send a webrtc_request so
    // they know to offer their stream once they start streaming.
    const instructorId = msg.user_id as string
    console.log(`[LiveRoom][LEARNER] peer_joined from instructor=${instructorId}, sending webrtc_request`)
    sendWs({ type: 'webrtc_request', target_user_id: instructorId })

  } else if (type === 'room_peers' && isInstructor.value) {
    const peers = (msg.peers ?? []) as { user_id: string }[]
    console.log(`[LiveRoom][INSTRUCTOR] room_peers count=${peers.length}`, peers)
    for (const peer of peers) {
      knownLearnerIds.add(peer.user_id)
      if (localStream.getTracks().length > 0) {
        await offerToLearner(peer.user_id)
      }
    }

  } else if (type === 'room_peers' && !isInstructor.value) {
    // Learner joined and found peers already in the room. Send a webrtc_request to
    // each peer so the instructor knows to send an offer. This covers the case where
    // the instructor is already in the room but hadn't started streaming yet when the
    // learner joined (so the peer_joined offer was suppressed), or where the initial
    // offer was lost. The instructor will call offerToLearner() if they have tracks.
    const peers = (msg.peers ?? []) as { user_id: string }[]
    console.log(`[LiveRoom][LEARNER] room_peers, requesting stream from ${peers.length} peer(s)`)
    for (const peer of peers) {
      sendWs({ type: 'webrtc_request', target_user_id: peer.user_id })
    }

  } else if (type === 'webrtc_request' && isInstructor.value) {
    const requesterId = msg.from_user_id as string
    knownLearnerIds.add(requesterId)
    if (localStream.getTracks().length > 0) {
      // Only create a new offer if there is no healthy peer connection already.
      // peer_joined (which fires just before room_peers reaches the learner) often
      // creates a PC first. Sending a second offer would close that in-progress PC,
      // cause the learner to send a mismatched answer, and throw in setRemoteDescription
      // — permanently killing the signaling queue before the try-catch was added.
      const existing = peerConnections.get(requesterId)
      const isHealthy = !!existing &&
        existing.connectionState !== 'failed' &&
        existing.connectionState !== 'closed' &&
        existing.connectionState !== 'disconnected'
      console.log(`[LiveRoom][INSTRUCTOR] webrtc_request from=${requesterId}, streaming=true, existingPc=${existing?.connectionState ?? 'none'}, skip=${isHealthy}`)
      if (!isHealthy) {
        await offerToLearner(requesterId)
      }
    } else {
      console.log(`[LiveRoom][INSTRUCTOR] webrtc_request from=${requesterId}, no local tracks yet — learner added to knownLearnerIds`)
    }

  } else if (type === 'webrtc_offer' && !isInstructor.value) {
    const instructorId = msg.from_user_id as string
    console.log(`[LiveRoom][LEARNER] received webrtc_offer from=${instructorId}`)
    const pc = createPeerConnectionFor(instructorId)
    await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp as RTCSessionDescriptionInit))
    console.log(`[LiveRoom][LEARNER] setRemoteDescription done, flushing ${iceCandidateQueue.get(instructorId)?.length ?? 0} queued ICE candidates`)
    for (const c of iceCandidateQueue.get(instructorId) ?? []) {
      try { await pc.addIceCandidate(new RTCIceCandidate(c)) } catch {}
    }
    iceCandidateQueue.delete(instructorId)
    const answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    console.log(`[LiveRoom][LEARNER] answer created, sending to instructor=${instructorId}`)
    sendWs({ type: 'webrtc_answer', sdp: answer, target_user_id: instructorId })

  } else if (type === 'webrtc_answer' && isInstructor.value) {
    const fromId = msg.from_user_id as string
    console.log(`[LiveRoom][INSTRUCTOR] received webrtc_answer from=${fromId}`)
    const pc = peerConnections.get(fromId)
    if (pc) {
      await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp as RTCSessionDescriptionInit))
      console.log(`[LiveRoom][INSTRUCTOR] setRemoteDescription(answer) done, flushing ${iceCandidateQueue.get(fromId)?.length ?? 0} queued ICE`)
      for (const c of iceCandidateQueue.get(fromId) ?? []) {
        try { await pc.addIceCandidate(new RTCIceCandidate(c)) } catch {}
      }
      iceCandidateQueue.delete(fromId)
    } else {
      console.warn(`[LiveRoom][INSTRUCTOR] webrtc_answer: no PC found for fromId=${fromId}`)
    }

  } else if (type === 'webrtc_ice') {
    const fromId = msg.from_user_id as string
    const candidate = msg.candidate as RTCIceCandidateInit
    const pc = peerConnections.get(fromId)
    if (pc?.remoteDescription) {
      try { await pc.addIceCandidate(new RTCIceCandidate(candidate)) } catch {}
    } else {
      const q = iceCandidateQueue.get(fromId) ?? []
      q.push(candidate)
      iceCandidateQueue.set(fromId, q)
    }

  } else if (type === 'peer_left' && isInstructor.value) {
    const uid = msg.user_id as string
    knownLearnerIds.delete(uid)
    const pc = peerConnections.get(uid)
    if (pc) { pc.close(); peerConnections.delete(uid) }
  }
}

// ── Local video preview ───────────────────────────────────────────────────────
// Called any time tracks are added/removed so the <video> element stays in sync
function attachLocalStream() {
  nextTick(() => {
    if (localVideo.value) {
      // Re-assigning the same object doesn't trigger a re-render in some browsers;
      // set to null first to force the element to pick up the new track list.
      localVideo.value.srcObject = null
      localVideo.value.srcObject = localStream
    }
  })
}

// ── Instructor: mic toggle ────────────────────────────────────────────────────
async function toggleMic() {
  if (micOn.value) {
    localStream.getAudioTracks().forEach(t => { t.stop(); localStream.removeTrack(t) })
    micOn.value = false
    attachLocalStream()
  } else {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true })
      s.getAudioTracks().forEach(t => localStream.addTrack(t))
      micOn.value = true
      attachLocalStream()
      await broadcastStream()
    } catch (err) {
      console.error('Mic access denied', err)
    }
  }
}

// ── Instructor: camera toggle ─────────────────────────────────────────────────
async function toggleCam() {
  if (camOn.value) {
    localStream.getVideoTracks().forEach(t => { t.stop(); localStream.removeTrack(t) })
    camOn.value = false
    screenSharing.value = false
    attachLocalStream()
  } else {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      s.getVideoTracks().forEach(t => localStream.addTrack(t))
      camOn.value = true
      attachLocalStream()
      await broadcastStream()
    } catch (err) {
      console.error('Camera access denied', err)
    }
  }
}

// ── Instructor: screen share toggle ──────────────────────────────────────────
async function toggleScreen() {
  if (screenSharing.value) {
    localStream.getVideoTracks().forEach(t => { t.stop(); localStream.removeTrack(t) })
    screenSharing.value = false
    camOn.value = false
    attachLocalStream()
  } else {
    try {
      const s = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true })
      // Remove any existing video tracks first
      localStream.getVideoTracks().forEach(t => { t.stop(); localStream.removeTrack(t) })
      s.getTracks().forEach(t => {
        localStream.addTrack(t)
        t.onended = () => {
          localStream.removeTrack(t)
          screenSharing.value = false
          camOn.value = false
          attachLocalStream()
        }
      })
      screenSharing.value = true
      camOn.value = false
      attachLocalStream()
      await broadcastStream()
    } catch (err) {
      console.error('Screen share denied or cancelled', err)
    }
  }
}

// ── WebRTC broadcast ──────────────────────────────────────────────────────────
// Called when instructor starts/changes their stream — always renegotiate with all known learners.
// Full renegotiation (instead of replaceTrack) is required because screen share uses a different
// codec profile than camera; replaceTrack alone does not trigger ontrack on the remote side.
async function broadcastStream() {
  if (!isInstructor.value || localStream.getTracks().length === 0) return
  for (const learnerId of knownLearnerIds) {
    await offerToLearner(learnerId)
  }
}

// ── Recording ─────────────────────────────────────────────────────────────────
function toggleRecording() {
  if (recording.value) {
    mediaRecorder?.stop()
    recording.value = false
    return
  }

  const tracks = localStream.getTracks()
  if (tracks.length === 0) {
    alert('Turn on your camera or screen share first, then start recording.')
    return
  }

  recordedChunks = []
  uploadState.uploading = false
  uploadState.done = false
  uploadState.error = ''

  const mimeType = getSupportedMimeType()
  mediaRecorder = new MediaRecorder(localStream, { mimeType })
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data) }
  mediaRecorder.onstop = () => uploadRecording(mimeType)
  mediaRecorder.start(1000)
  recording.value = true
}

async function uploadRecording(mimeType: string) {
  if (recordedChunks.length === 0) return  // nothing was recorded (e.g. MediaRecorder stopped immediately)
  uploadState.uploading = true
  uploadState.error = ''
  try {
    const type = mimeType || 'video/webm'
    const blob = new Blob(recordedChunks, { type })
    if (blob.size === 0) return
    const durationSeconds = Math.round(blob.size / 50000) // rough estimate

    // POST multipart to backend — backend writes to MinIO server-side,
    // avoiding the internal minio:9000 hostname that is unreachable from the browser.
    await sessionsApi.uploadRecordingDirect(props.session.id, blob, type, durationSeconds)
    uploadState.done = true
  } catch (err: any) {
    uploadState.error = err.message ?? 'Upload failed'
  } finally {
    uploadState.uploading = false
  }
}

function getSupportedMimeType(): string {
  const types = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm']
  return types.find(t => MediaRecorder.isTypeSupported(t)) ?? ''
}

// ── Cleanup ───────────────────────────────────────────────────────────────────
onUnmounted(() => {
  _removeHandler()
  localStream.getTracks().forEach(t => t.stop())
  if (recording.value) mediaRecorder?.stop()
  peerConnections.forEach(pc => pc.close())
  peerConnections.clear()
  knownLearnerIds.clear()
  iceCandidateQueue.clear()
  _sigQueue.length = 0
})
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[60] bg-black/90 flex flex-col">

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 bg-gray-900 border-b border-white/10 shrink-0">
        <div class="flex items-center gap-3">
          <div class="h-2.5 w-2.5 rounded-full animate-pulse"
               :class="connectionStatus === 'connected' ? 'bg-green-400' : 'bg-yellow-400'" />
          <h2 class="text-white font-semibold">{{ session.course_title }} — Live Room</h2>
          <StatusBadge v-if="roomState" :status="roomState.session_status" />
        </div>
        <div class="flex items-center gap-4 text-sm text-gray-300">
          <span v-if="roomState">{{ roomState.checked_in_count ?? 0 }} / {{ roomState.enrolled_count }} attendees</span>
          <component :is="connectionStatus === 'connected' ? Wifi : WifiOff" class="h-4 w-4"
                     :class="connectionStatus === 'connected' ? 'text-green-400' : 'text-yellow-400'" />
          <button @click="emit('close')" class="p-1 rounded text-gray-400 hover:text-white hover:bg-white/10">
            <X class="h-5 w-5" />
          </button>
        </div>
      </div>

      <!-- Session ended banner -->
      <div v-if="isCompleted" class="bg-blue-600 text-white text-center py-3 text-sm font-medium shrink-0">
        This session has ended. Thank you for participating!
      </div>

      <!-- Main -->
      <div class="flex flex-1 overflow-hidden">

        <!-- Video + controls -->
        <div class="flex-1 flex flex-col items-center justify-center bg-black gap-4 p-4">

          <!-- Instructor: local preview -->
          <div v-if="isInstructor"
               class="relative w-full max-w-3xl aspect-video bg-gray-900 rounded-lg overflow-hidden border border-white/10">
            <video ref="localVideo" autoplay muted playsinline class="w-full h-full object-contain" />
            <div v-if="!hasStream"
                 class="absolute inset-0 flex items-center justify-center text-gray-500 text-sm select-none">
              Enable camera or screen share to preview your stream
            </div>
            <div class="absolute top-2 left-2 text-xs bg-black/60 text-white px-2 py-0.5 rounded">
              You (local preview)
            </div>
          </div>

          <!-- Learner: remote stream -->
          <div v-if="!isInstructor"
               class="relative w-full max-w-3xl aspect-video bg-gray-900 rounded-lg overflow-hidden border border-white/10">
            <video ref="remoteVideo" autoplay playsinline class="w-full h-full object-contain" />
            <div v-if="!hasRemoteStream"
                 class="absolute inset-0 flex items-center justify-center text-gray-500 text-sm select-none">
              Waiting for instructor stream…
            </div>
          </div>

          <!-- Instructor controls -->
          <div v-if="isInstructor" class="flex flex-wrap items-center justify-center gap-3">
            <button @click="toggleMic"
                    :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                             micOn ? 'bg-white text-black hover:bg-gray-200' : 'bg-white/10 text-white hover:bg-white/20']">
              <component :is="micOn ? Mic : MicOff" class="h-4 w-4" />
              {{ micOn ? 'Mute' : 'Unmute' }}
            </button>

            <button @click="toggleCam"
                    :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                             camOn ? 'bg-white text-black hover:bg-gray-200' : 'bg-white/10 text-white hover:bg-white/20']">
              <component :is="camOn ? Video : VideoOff" class="h-4 w-4" />
              {{ camOn ? 'Stop Camera' : 'Start Camera' }}
            </button>

            <button @click="toggleScreen"
                    :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                             screenSharing ? 'bg-blue-500 text-white hover:bg-blue-600' : 'bg-white/10 text-white hover:bg-white/20']">
              <Monitor class="h-4 w-4" />
              {{ screenSharing ? 'Stop Share' : 'Share Screen' }}
            </button>

            <button @click="toggleRecording"
                    :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                             recording ? 'bg-red-600 text-white hover:bg-red-700 animate-pulse' : 'bg-white/10 text-white hover:bg-white/20']">
              <component :is="recording ? StopCircle : Circle" class="h-4 w-4" />
              {{ recording ? 'Stop Recording' : 'Record' }}
            </button>
          </div>

          <p v-if="recording" class="text-red-400 text-xs animate-pulse">● Recording…</p>
          <p v-if="uploadState.uploading" class="text-yellow-400 text-xs">⬆ Uploading recording to storage…</p>
          <p v-if="uploadState.done" class="text-green-400 text-xs">✓ Recording saved to storage</p>
          <p v-if="uploadState.error" class="text-red-400 text-xs">Upload error: {{ uploadState.error }}</p>
        </div>

        <!-- Activity feed sidebar -->
        <div class="w-72 border-l border-white/10 flex flex-col bg-gray-900 shrink-0">
          <div class="px-4 py-3 border-b border-white/10 text-sm font-medium text-gray-300">Activity</div>
          <div class="flex-1 overflow-y-auto p-3 flex flex-col-reverse gap-2">
            <TransitionGroup name="event">
              <div v-for="(evt, i) in events.filter(e => !!eventLabels[e.type]?.(e.payload))" :key="i"
                   :class="['flex items-start gap-2 p-2 rounded text-xs',
                            evt.type === 'session_status_changed' ? 'bg-blue-900/50 text-blue-200' : 'bg-white/5 text-gray-300']">
                <span class="text-gray-500 shrink-0">{{ evt.timestamp.toLocaleTimeString() }}</span>
                <span>{{ eventLabel(evt) }}</span>
              </div>
            </TransitionGroup>
            <div v-if="events.length === 0" class="text-center text-gray-600 py-8 text-xs">Waiting for activity…</div>
          </div>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.event-enter-active { transition: all 0.2s ease; }
.event-enter-from { opacity: 0; transform: translateY(-8px); }
</style>
