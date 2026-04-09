<script setup lang="ts">
import { ref } from 'vue'
import { useForm } from 'vee-validate'
import * as yup from 'yup'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'

const auth = useAuthStore()
const ui = useUiStore()

const schema = yup.object({
  currentPassword: yup.string().required('Required'),
  newPassword: yup.string().min(12, 'Min 12 chars')
    .matches(/[A-Z]/, 'Needs uppercase letter')
    .matches(/[a-z]/, 'Needs lowercase letter')
    .matches(/[0-9]/, 'Needs a digit')
    .matches(/[^A-Za-z0-9]/, 'Needs a special character')
    .required('Required'),
  confirm: yup.string().oneOf([yup.ref('newPassword')], 'Passwords must match').required('Required'),
})

const { defineField, handleSubmit, errors, resetForm } = useForm({ validationSchema: schema })
const [currentPassword, cpAttrs] = defineField('currentPassword')
const [newPassword, npAttrs] = defineField('newPassword')
const [confirm, cfAttrs] = defineField('confirm')
const isSubmitting = ref(false)

const onSubmit = handleSubmit(async (values) => {
  isSubmitting.value = true
  try {
    await auth.changePassword(values.currentPassword, values.newPassword)
    ui.addToast('Password changed successfully', 'success')
    resetForm()
  } catch (e: any) {
    ui.addToast(e.message ?? 'Failed to change password', 'error')
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <AppLayout>
    <div class="max-w-md">
      <h1 class="text-xl font-semibold text-foreground mb-6">Change Password</h1>
      <div class="bg-card border border-border rounded-lg p-6">
        <form @submit.prevent="onSubmit" class="flex flex-col gap-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-1">Current Password</label>
            <input v-model="currentPassword" v-bind="cpAttrs" type="password"
              class="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              :class="errors.currentPassword ? 'border-destructive' : ''" />
            <p v-if="errors.currentPassword" class="text-xs text-destructive mt-1">{{ errors.currentPassword }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-1">New Password</label>
            <input v-model="newPassword" v-bind="npAttrs" type="password"
              class="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              :class="errors.newPassword ? 'border-destructive' : ''" />
            <p v-if="errors.newPassword" class="text-xs text-destructive mt-1">{{ errors.newPassword }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-1">Confirm New Password</label>
            <input v-model="confirm" v-bind="cfAttrs" type="password"
              class="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              :class="errors.confirm ? 'border-destructive' : ''" />
            <p v-if="errors.confirm" class="text-xs text-destructive mt-1">{{ errors.confirm }}</p>
          </div>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="py-2 px-4 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <div v-if="isSubmitting" class="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
            Update Password
          </button>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
