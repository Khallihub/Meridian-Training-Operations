<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminApi } from '@/api/endpoints/admin'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()
const editId = route.params.id as string | undefined
const isEdit = !!editId && editId !== 'new'

const form = ref({ username: '', role: 'learner', password: '', email: '', phone: '', is_active: true })
const isSubmitting = ref(false)

onMounted(async () => {
  if (isEdit) {
    const u = await adminApi.getUser(editId!)
    // phone/email come back masked (e.g. "***-***-1234") — clear them so
    // the admin only overwrites if they deliberately type a new value
    Object.assign(form.value, { ...u, phone: '', email: '' })
  }
})

async function handleSubmit() {
  isSubmitting.value = true
  try {
    if (isEdit) {
      const patch: Record<string, unknown> = { role: form.value.role, is_active: form.value.is_active }
      if (form.value.email) patch.email = form.value.email
      if (form.value.phone) patch.phone = form.value.phone
      await adminApi.updateUser(editId!, patch as any)
      ui.addToast('User updated', 'success')
    } else {
      await adminApi.createUser(form.value as any)
      ui.addToast('User created', 'success')
    }
    router.push('/admin/users')
  } catch (e: any) { ui.addToast(e.message, 'error') }
  finally { isSubmitting.value = false }
}
</script>

<template>
  <AppLayout>
    <div class="max-w-md">
      <h1 class="text-xl font-semibold text-foreground mb-6">{{ isEdit ? 'Edit User' : 'New User' }}</h1>
      <div class="bg-card border border-border rounded-lg p-6">
        <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Username</label>
            <input v-model="form.username" :disabled="isEdit" required class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm disabled:opacity-50" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Role</label>
            <select v-model="form.role" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm">
              <option v-for="r in ['admin','instructor','learner','finance','dataops']" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
          <div v-if="!isEdit">
            <label class="block text-sm font-medium mb-1">Password</label>
            <input v-model="form.password" type="password" required minlength="12" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Email{{ isEdit ? ' (leave blank to keep existing)' : '' }}</label>
            <input v-model="form.email" type="email" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Phone{{ isEdit ? ' (leave blank to keep existing)' : '' }}</label>
            <input v-model="form.phone" type="tel" placeholder="e.g. +1 555 000 1234" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
          </div>
          <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="form.is_active" class="rounded" /> Active</label>
          <div class="flex gap-3 pt-2">
            <button type="submit" :disabled="isSubmitting" class="px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90 disabled:opacity-50">
              {{ isEdit ? 'Save' : 'Create' }}
            </button>
            <button type="button" @click="router.back()" class="px-4 py-2 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
