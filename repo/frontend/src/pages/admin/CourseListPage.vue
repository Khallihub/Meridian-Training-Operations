<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi, type Course } from '@/api/endpoints/admin'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'

const ui = useUiStore()
const courses = ref<Course[]>([])
const showForm = ref(false)
const form = ref({ title: '', description: '', duration_minutes: 60, price: 0, category: '', is_active: true })
const editingId = ref<string | null>(null)

onMounted(async () => { courses.value = await adminApi.getCourses() })

function startEdit(c: Course) {
  editingId.value = c.id
  Object.assign(form.value, { title: c.title, description: c.description, duration_minutes: c.duration_minutes, price: c.price, category: c.category, is_active: c.is_active })
  showForm.value = true
}

function cancelForm() {
  showForm.value = false
  editingId.value = null
  Object.assign(form.value, { title: '', description: '', duration_minutes: 60, price: 0, category: '', is_active: true })
}

async function handleSubmit() {
  try {
    if (editingId.value) {
      const updated = await adminApi.updateCourse(editingId.value, form.value)
      const idx = courses.value.findIndex(c => c.id === editingId.value)
      if (idx !== -1) courses.value[idx] = updated
      ui.addToast('Course updated', 'success')
    } else {
      const c = await adminApi.createCourse(form.value)
      courses.value.unshift(c)
      ui.addToast('Course created', 'success')
    }
    cancelForm()
  } catch (e: any) { ui.addToast(e.message, 'error') }
}
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Courses</h1>
      <button @click="showForm ? cancelForm() : (showForm = true)" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
        {{ showForm ? 'Cancel' : '+ New' }}
      </button>
    </div>

    <div v-if="showForm" class="bg-card border border-border rounded-lg p-5 mb-5">
      <h2 class="text-sm font-medium text-foreground mb-3">{{ editingId ? 'Edit Course' : 'New Course' }}</h2>
      <form @submit.prevent="handleSubmit" class="flex flex-col gap-3">
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs mb-1">Title</label><input v-model="form.title" required class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
          <div><label class="block text-xs mb-1">Category</label><input v-model="form.category" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
        </div>
        <div><label class="block text-xs mb-1">Description</label><textarea v-model="form.description" rows="2" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs mb-1">Duration (min)</label><input v-model.number="form.duration_minutes" type="number" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
          <div><label class="block text-xs mb-1">Price ($)</label><input v-model.number="form.price" type="number" step="0.01" min="0" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" /></div>
        </div>
        <div class="flex gap-3">
          <button type="submit" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">{{ editingId ? 'Save' : 'Create' }}</button>
          <button type="button" @click="cancelForm" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm">Cancel</button>
        </div>
      </form>
    </div>

    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Title</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Category</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Duration</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground">Price</th>
            <th class="px-4 py-3 text-right font-medium text-muted-foreground"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in courses" :key="c.id" class="border-t border-border hover:bg-muted/30">
            <td class="px-4 py-3 font-medium text-foreground">{{ c.title }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ c.category }}</td>
            <td class="px-4 py-3 text-right text-muted-foreground">{{ c.duration_minutes }}m</td>
            <td class="px-4 py-3 text-right text-muted-foreground">${{ c.price?.toFixed(2) ?? '0.00' }}</td>
            <td class="px-4 py-3 text-right">
              <button @click="startEdit(c)" class="text-xs px-2 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-accent">Edit</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
