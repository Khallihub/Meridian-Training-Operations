<script setup lang="ts">
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

const props = defineProps<{
  currentPage: number
  totalCount: number
  pageSize: number
}>()

const emit = defineEmits<{
  (e: 'page-change', page: number): void
  (e: 'size-change', size: number): void
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.totalCount / props.pageSize)))

const from = computed(() => (props.currentPage - 1) * props.pageSize + 1)
const to = computed(() => Math.min(props.currentPage * props.pageSize, props.totalCount))
</script>

<template>
  <div class="flex items-center justify-between text-sm text-muted-foreground">
    <span>{{ from }}–{{ to }} of {{ totalCount.toLocaleString() }}</span>
    <div class="flex items-center gap-1">
      <select
        :value="pageSize"
        @change="emit('size-change', Number(($event.target as HTMLSelectElement).value))"
        class="text-sm border border-border rounded px-1 py-0.5 bg-background"
      >
        <option>10</option>
        <option>25</option>
        <option>50</option>
      </select>
      <button
        :disabled="currentPage <= 1"
        @click="emit('page-change', currentPage - 1)"
        class="p-1 rounded hover:bg-accent disabled:opacity-40"
      >
        <ChevronLeft class="h-4 w-4" />
      </button>
      <span class="px-2">{{ currentPage }} / {{ totalPages }}</span>
      <button
        :disabled="currentPage >= totalPages"
        @click="emit('page-change', currentPage + 1)"
        class="p-1 rounded hover:bg-accent disabled:opacity-40"
      >
        <ChevronRight class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>
