<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi, type UserRecord } from '@/api/endpoints/admin'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'
import { Plus } from 'lucide-vue-next'

const router = useRouter()
const ui = useUiStore()
const users = ref<UserRecord[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)

const roleBadge: Record<string, string> = {
  admin: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  instructor: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  learner: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  finance: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  dataops: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await adminApi.getUsers({ page: page.value, page_size: 25 })
    users.value = res.items
    total.value = res.total
  } finally { loading.value = false }
}

async function toggleActive(u: UserRecord) {
  try {
    const updated = await adminApi.updateUser(u.id, { is_active: !u.is_active })
    const idx = users.value.findIndex(x => x.id === u.id)
    if (idx !== -1) users.value[idx] = updated
  } catch (e: any) { ui.addToast(e.message, 'error') }
}
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-foreground">Users</h1>
      <RouterLink to="/admin/users/new" class="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90">
        <Plus class="h-4 w-4" /> New User
      </RouterLink>
    </div>

    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Username</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Role</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Phone</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Last Login</th>
            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Active</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="5" class="py-8 text-center text-muted-foreground">Loading…</td></tr>
          <tr v-for="u in users" :key="u.id" class="border-t border-border hover:bg-muted/30 cursor-pointer" @click="router.push(`/admin/users/${u.id}`)">
            <td class="px-4 py-3 font-medium text-foreground">{{ u.username }}</td>
            <td class="px-4 py-3">
              <span :class="['text-xs px-2 py-0.5 rounded font-medium', roleBadge[u.role] ?? '']">{{ u.role }}</span>
            </td>
            <td class="px-4 py-3 font-mono text-xs text-muted-foreground">{{ u.phone ?? '—' }}</td>
            <td class="px-4 py-3 text-xs text-muted-foreground">{{ u.last_login?.slice(0, 16) ?? 'Never' }}</td>
            <td class="px-4 py-3">
              <button @click.stop="toggleActive(u)" :class="['text-xs px-2 py-0.5 rounded font-medium', u.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-gray-100 text-gray-600 dark:bg-gray-800']">
                {{ u.is_active ? 'Active' : 'Inactive' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
