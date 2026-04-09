<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useForm } from 'vee-validate'
import * as yup from 'yup'
import { useAuthStore } from '@/stores/auth'
import AuthLayout from '@/layouts/AuthLayout.vue'
import ErrorAlert from '@/components/shared/ErrorAlert.vue'

const router = useRouter()
const auth = useAuthStore()

const schema = yup.object({ username: yup.string().required(), password: yup.string().required() })
const { defineField, handleSubmit, errors } = useForm({ validationSchema: schema })
const [username, usernameAttrs] = defineField('username')
const [password, passwordAttrs] = defineField('password')

const errorMsg = ref('')
const isSubmitting = ref(false)
const lockedUntil = ref<string | null>(null)

const ROLE_HOME: Record<string, string> = {
  admin: '/admin/dashboard', instructor: '/instructor/dashboard',
  learner: '/learner/dashboard', finance: '/finance/dashboard', dataops: '/dataops/dashboard',
}

const onSubmit = handleSubmit(async (values) => {
  isSubmitting.value = true
  errorMsg.value = ''
  lockedUntil.value = null
  try {
    await auth.login(values.username, values.password)
    router.push(ROLE_HOME[auth.role!] ?? '/')
  } catch (e: any) {
    if (e.statusCode === 423) {
      // Account locked; parse locked_until from error detail
      lockedUntil.value = e.errors?.locked_until ?? 'a few minutes'
    } else {
      errorMsg.value = e.message ?? 'Invalid username or password'
    }
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <AuthLayout>
    <h2 class="text-xl font-semibold text-foreground mb-6">Sign in</h2>

    <ErrorAlert v-if="errorMsg" :message="errorMsg" class="mb-4" />

    <div v-if="lockedUntil" class="mb-4 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950 border border-yellow-300 text-yellow-800 dark:text-yellow-200 text-sm">
      Account locked. Try again at <strong>{{ lockedUntil }}</strong>.
    </div>

    <form @submit.prevent="onSubmit" class="flex flex-col gap-4">
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Username</label>
        <input
          v-model="username" v-bind="usernameAttrs"
          type="text" autocomplete="username"
          class="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          :class="errors.username ? 'border-destructive' : ''"
        />
        <p v-if="errors.username" class="text-xs text-destructive mt-1">{{ errors.username }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Password</label>
        <input
          v-model="password" v-bind="passwordAttrs"
          type="password" autocomplete="current-password"
          class="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          :class="errors.password ? 'border-destructive' : ''"
        />
        <p v-if="errors.password" class="text-xs text-destructive mt-1">{{ errors.password }}</p>
      </div>

      <button
        type="submit"
        :disabled="isSubmitting"
        class="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
      >
        <div v-if="isSubmitting" class="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
        {{ isSubmitting ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
  </AuthLayout>
</template>
