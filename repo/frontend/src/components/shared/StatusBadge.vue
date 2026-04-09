<script setup lang="ts">
defineProps<{ status: string }>()

const variants: Record<string, string> = {
  // Session statuses
  scheduled: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  live:       'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  completed:  'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  cancelled:  'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',

  // Booking statuses
  pending:     'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  confirmed:   'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  rescheduled: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  no_show:     'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',

  // Payment / refund statuses
  paid:     'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  failed:   'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  refunded: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  approved: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',

  // Upload statuses
  processing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  ready:      'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',

  // Ingestion / job statuses
  success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  failure: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  late:    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
}
</script>

<template>
  <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', variants[status] ?? 'bg-gray-100 text-gray-700']">
    {{ status.replace(/_/g, ' ') }}
  </span>
</template>
