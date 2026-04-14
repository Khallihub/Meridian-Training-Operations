<script setup lang="ts">
defineProps<{ status: string }>()

const variants: Record<string, string> = {
  // Session statuses
  draft:                 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  scheduled:             'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  live:                  'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  ended:                 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  recording_processing:  'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  recording_published:   'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  closed_no_recording:   'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
  canceled:              'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  archived:              'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',

  // Booking statuses
  requested:        'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  confirmed:        'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  rescheduled_out:  'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  completed:        'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  no_show:          'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',

  // Order statuses
  awaiting_payment: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  paid:             'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  closed_unpaid:    'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  refund_pending:   'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  refunded_partial: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  refunded_full:    'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',

  // Refund statuses
  pending_review:   'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  approved:         'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  processing:       'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  rejected:         'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  failed:           'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',

  // Payment status
  pending:  'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',

  // Upload statuses
  ready:  'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',

  // Ingestion / job statuses
  succeeded:      'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  partial_failed: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  resolved:       'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  running:        'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  queued:         'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  late:           'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
}
</script>

<template>
  <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', variants[status] ?? 'bg-gray-100 text-gray-700']">
    {{ status.replace(/_/g, ' ') }}
  </span>
</template>
