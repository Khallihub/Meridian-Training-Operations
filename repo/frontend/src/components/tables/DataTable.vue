<script setup lang="ts">
import { ref } from 'vue'
import Pagination from '@/components/shared/Pagination.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'

export interface Column {
  key: string
  label: string
  sortable?: boolean
  class?: string
}

const props = defineProps<{
  columns: Column[]
  rows: Record<string, unknown>[]
  loading?: boolean
  totalCount?: number
  pageSize?: number
  currentPage?: number
  emptyTitle?: string
  emptyDescription?: string
}>()

const emit = defineEmits<{
  (e: 'page-change', page: number): void
  (e: 'size-change', size: number): void
  (e: 'sort', key: string): void
  (e: 'row-click', row: Record<string, unknown>): void
}>()

const sortKey = ref('')
const sortAsc = ref(true)

function handleSort(key: string) {
  if (sortKey.value === key) { sortAsc.value = !sortAsc.value }
  else { sortKey.value = key; sortAsc.value = true }
  emit('sort', key)
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :class="['px-4 py-3 text-left font-medium text-muted-foreground whitespace-nowrap', col.class, col.sortable ? 'cursor-pointer select-none hover:text-foreground' : '']"
              @click="col.sortable ? handleSort(col.key) : undefined"
            >
              <span class="flex items-center gap-1">
                {{ col.label }}
                <span v-if="col.sortable && sortKey === col.key" class="text-xs">{{ sortAsc ? '▲' : '▼' }}</span>
              </span>
            </th>
            <th v-if="$slots.actions" class="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr>
              <td :colspan="columns.length + ($slots.actions ? 1 : 0)" class="py-12">
                <LoadingSpinner />
              </td>
            </tr>
          </template>
          <template v-else-if="rows.length === 0">
            <tr>
              <td :colspan="columns.length + ($slots.actions ? 1 : 0)">
                <EmptyState :title="emptyTitle" :description="emptyDescription" />
              </td>
            </tr>
          </template>
          <template v-else>
            <tr
              v-for="(row, i) in rows"
              :key="i"
              class="border-t border-border hover:bg-muted/30 transition-colors"
              :class="$attrs?.['onRow-click'] ? 'cursor-pointer' : ''"
              @click="emit('row-click', row)"
            >
              <td
                v-for="col in columns"
                :key="col.key"
                :class="['px-4 py-3 text-foreground', col.class]"
              >
                <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                  {{ row[col.key] ?? '—' }}
                </slot>
              </td>
              <td v-if="$slots.actions" class="px-4 py-3 text-right">
                <slot name="actions" :row="row" />
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <Pagination
      v-if="totalCount !== undefined && pageSize && currentPage"
      :current-page="currentPage"
      :total-count="totalCount"
      :page-size="pageSize"
      @page-change="emit('page-change', $event)"
      @size-change="emit('size-change', $event)"
    />
  </div>
</template>
