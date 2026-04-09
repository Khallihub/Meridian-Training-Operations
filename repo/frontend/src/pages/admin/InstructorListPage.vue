<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi, type Instructor } from '@/api/endpoints/admin'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'

const ui = useUiStore()
const instructors = ref<Instructor[]>([])
const showForm = ref(false)
const eligibleUsers = ref<{ id: string; username: string }[]>([])
const form = ref({ user_id: '', bio: '' })
const submitting = ref(false)

onMounted(async () => {
  instructors.value = await adminApi.getInstructors()
})

async function openForm() {
  const res = await adminApi.getUsers({ role: 'instructor', page_size: 200 })
  const existingUserIds = new Set(instructors.value.map(i => i.user_id))
  eligibleUsers.value = res.items
    .filter(u => u.is_active && !existingUserIds.has(u.id))
    .map(u => ({ id: u.id, username: u.username }))
  form.value = { user_id: '', bio: '' }
  showForm.value = true
}

async function handleCreate() {
  if (!form.value.user_id) {
    ui.addToast('Please select a user', 'error')
    return
  }
  submitting.value = true
  try {
    const inst = await adminApi.createInstructor({ user_id: form.value.user_id, bio: form.value.bio || undefined })
    instructors.value.unshift(inst)
    showForm.value = false
    ui.addToast('Instructor created', 'success')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Instructors</h1>
      <button @click="openForm" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">+ New</button>
    </div>

    <div v-if="showForm" class="bg-card border border-border rounded-lg p-5 mb-5">
      <h2 class="text-sm font-medium text-foreground mb-3">Link instructor user</h2>
      <form @submit.prevent="handleCreate" class="flex flex-col gap-3">
        <div>
          <label class="block text-xs mb-1 text-muted-foreground">User (role = instructor)</label>
          <select v-model="form.user_id" required class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm">
            <option value="">Select user…</option>
            <option v-for="u in eligibleUsers" :key="u.id" :value="u.id">{{ u.username }}</option>
          </select>
          <p v-if="eligibleUsers.length === 0" class="text-xs text-muted-foreground mt-1">
            No eligible users found. Create a user with role <code>instructor</code> first.
          </p>
        </div>
        <div>
          <label class="block text-xs mb-1 text-muted-foreground">Bio (optional)</label>
          <textarea v-model="form.bio" rows="2" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" />
        </div>
        <div class="flex gap-3">
          <button type="submit" :disabled="submitting" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm disabled:opacity-50">
            {{ submitting ? 'Creating…' : 'Create' }}
          </button>
          <button type="button" @click="showForm = false" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm">Cancel</button>
        </div>
      </form>
    </div>

    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Username</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Bio</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Active</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="instructors.length === 0">
            <td colspan="3" class="px-4 py-8 text-center text-muted-foreground text-sm">No instructors yet. Click "+ New" to link one.</td>
          </tr>
          <tr v-for="i in instructors" :key="i.id" class="border-t border-border hover:bg-muted/30">
            <td class="px-4 py-3 font-medium text-foreground">{{ i.username }}</td>
            <td class="px-4 py-3 text-muted-foreground text-xs max-w-xs truncate">{{ i.bio ?? '—' }}</td>
            <td class="px-4 py-3 text-xs" :class="i.is_active ? 'text-green-600' : 'text-muted-foreground'">{{ i.is_active ? 'Yes' : 'No' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
