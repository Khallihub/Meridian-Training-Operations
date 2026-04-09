<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-vue-next'

const ui = useUiStore()

const icons = { success: CheckCircle, error: XCircle, warning: AlertTriangle, info: Info }
const colors = {
  success: 'border-green-500 bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-200',
  error: 'border-red-500 bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200',
  warning: 'border-yellow-500 bg-yellow-50 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200',
  info: 'border-blue-500 bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200',
}
</script>

<template>
  <div class="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
    <TransitionGroup name="toast">
      <div
        v-for="toast in ui.toasts"
        :key="toast.id"
        :class="['flex items-start gap-3 p-3 rounded-lg border-l-4 shadow-lg', colors[toast.type]]"
      >
        <component :is="icons[toast.type]" class="h-4 w-4 mt-0.5 shrink-0" />
        <span class="text-sm flex-1">{{ toast.message }}</span>
        <button @click="ui.removeToast(toast.id)" class="shrink-0 opacity-60 hover:opacity-100">
          <X class="h-4 w-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { opacity: 0; transform: translateX(100%); }
.toast-leave-to { opacity: 0; transform: translateX(100%); }
</style>
