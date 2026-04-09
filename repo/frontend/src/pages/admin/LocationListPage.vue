<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi, type Location, type Room } from '@/api/endpoints/admin'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'

const ui = useUiStore()
const locations = ref<Location[]>([])
const showLocationForm = ref(false)
const locationForm = ref({ name: '', address: '', timezone: 'UTC' })

// Room state keyed by location id
const expandedLocation = ref<string | null>(null)
const roomsByLocation = ref<Record<string, Room[]>>({})
const showRoomForm = ref<string | null>(null)
const roomForm = ref({ name: '', capacity: 20 })

onMounted(async () => { locations.value = await adminApi.getLocations() })

async function handleCreateLocation() {
  try {
    const loc = await adminApi.createLocation(locationForm.value)
    locations.value.unshift(loc)
    showLocationForm.value = false
    Object.assign(locationForm.value, { name: '', address: '', timezone: 'UTC' })
    ui.addToast('Location created', 'success')
  } catch (e: any) { ui.addToast(e.message, 'error') }
}

async function toggleRooms(locId: string) {
  if (expandedLocation.value === locId) {
    expandedLocation.value = null
    return
  }
  expandedLocation.value = locId
  if (!roomsByLocation.value[locId]) {
    roomsByLocation.value[locId] = await adminApi.getRooms(locId)
  }
}

async function handleCreateRoom(locId: string) {
  try {
    const room = await adminApi.createRoom(locId, roomForm.value)
    roomsByLocation.value[locId] = [...(roomsByLocation.value[locId] ?? []), room]
    showRoomForm.value = null
    roomForm.value = { name: '', capacity: 20 }
    ui.addToast('Room created', 'success')
  } catch (e: any) { ui.addToast(e.message, 'error') }
}
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Locations</h1>
      <button @click="showLocationForm = !showLocationForm" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">+ New Location</button>
    </div>

    <div v-if="showLocationForm" class="bg-card border border-border rounded-lg p-5 mb-5">
      <form @submit.prevent="handleCreateLocation" class="flex flex-col gap-3">
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs mb-1">Name</label><input v-model="locationForm.name" required class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
          <div><label class="block text-xs mb-1">Timezone</label><input v-model="locationForm.timezone" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
        </div>
        <div><label class="block text-xs mb-1">Address</label><input v-model="locationForm.address" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
        <div class="flex gap-3">
          <button type="submit" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Create</button>
          <button type="button" @click="showLocationForm = false" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm">Cancel</button>
        </div>
      </form>
    </div>

    <div class="space-y-3">
      <div v-for="l in locations" :key="l.id" class="rounded-lg border border-border bg-card overflow-hidden">
        <!-- Location row -->
        <div class="flex items-center justify-between px-4 py-3 hover:bg-muted/30">
          <div class="flex items-center gap-4 flex-1 min-w-0">
            <span class="font-medium text-foreground">{{ l.name }}</span>
            <span class="text-xs text-muted-foreground truncate">{{ l.address }}</span>
            <span class="font-mono text-xs text-muted-foreground shrink-0">{{ l.timezone }}</span>
            <span class="text-xs shrink-0" :class="l.is_active ? 'text-green-600' : 'text-muted-foreground'">{{ l.is_active ? 'Active' : 'Inactive' }}</span>
          </div>
          <button @click="toggleRooms(l.id)" class="ml-4 px-2 py-1 text-xs rounded border border-border text-muted-foreground hover:text-foreground hover:bg-accent shrink-0">
            {{ expandedLocation === l.id ? 'Hide Rooms' : 'Rooms' }}
          </button>
        </div>

        <!-- Rooms panel -->
        <div v-if="expandedLocation === l.id" class="border-t border-border bg-muted/20 px-4 py-3">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Rooms</span>
            <button @click="showRoomForm = showRoomForm === l.id ? null : l.id" class="px-2 py-0.5 text-xs bg-primary text-primary-foreground rounded hover:opacity-90">+ Add Room</button>
          </div>

          <!-- Add room form -->
          <div v-if="showRoomForm === l.id" class="mb-3 p-3 bg-card border border-border rounded">
            <form @submit.prevent="handleCreateRoom(l.id)" class="flex items-end gap-3">
              <div class="flex-1"><label class="block text-xs mb-1">Room name</label><input v-model="roomForm.name" required placeholder="e.g. Room A" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
              <div class="w-28"><label class="block text-xs mb-1">Capacity</label><input v-model.number="roomForm.capacity" type="number" min="1" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
              <button type="submit" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Create</button>
              <button type="button" @click="showRoomForm = null" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm">Cancel</button>
            </form>
          </div>

          <!-- Room list -->
          <div v-if="roomsByLocation[l.id]?.length" class="space-y-1">
            <div v-for="r in roomsByLocation[l.id]" :key="r.id" class="flex items-center gap-4 text-sm py-1">
              <span class="font-medium text-foreground w-40 truncate">{{ r.name }}</span>
              <span class="text-xs text-muted-foreground">Cap: {{ r.capacity }}</span>
              <span class="text-xs" :class="r.is_active ? 'text-green-600' : 'text-muted-foreground'">{{ r.is_active ? 'Active' : 'Inactive' }}</span>
            </div>
          </div>
          <p v-else-if="roomsByLocation[l.id]?.length === 0" class="text-xs text-muted-foreground">No rooms yet.</p>
        </div>
      </div>

      <p v-if="locations.length === 0" class="text-sm text-muted-foreground text-center py-8">No locations yet.</p>
    </div>
  </AppLayout>
</template>
