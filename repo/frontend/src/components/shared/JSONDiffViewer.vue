<script setup lang="ts">
import { computed } from 'vue'
import VueJsonPretty from 'vue-json-pretty'
import 'vue-json-pretty/lib/styles.css'

const props = defineProps<{
  oldValue: Record<string, unknown> | null
  newValue: Record<string, unknown> | null
}>()

// Compute which keys changed
const changedKeys = computed(() => {
  const old = props.oldValue ?? {}
  const nw = props.newValue ?? {}
  const keys = new Set([...Object.keys(old), ...Object.keys(nw)])
  const changed: string[] = []
  for (const k of keys) {
    if (JSON.stringify(old[k]) !== JSON.stringify(nw[k])) changed.push(k)
  }
  return changed
})

// Build highlighted diff objects
const oldHighlighted = computed(() => {
  if (!props.oldValue) return null
  const result: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(props.oldValue)) {
    result[k] = changedKeys.value.includes(k) ? { _changed: true, value: v } : v
  }
  return result
})

const newHighlighted = computed(() => {
  if (!props.newValue) return null
  const result: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(props.newValue)) {
    result[k] = changedKeys.value.includes(k) ? { _changed: true, value: v } : v
  }
  return result
})
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div>
      <p class="text-xs font-medium text-muted-foreground uppercase mb-2">Before</p>
      <div class="rounded-lg border border-border bg-muted/30 p-3 overflow-auto max-h-64 text-xs">
        <VueJsonPretty
          v-if="oldValue"
          :data="oldValue"
          :deep="3"
          :show-length="true"
          :highlight-selected-node="false"
        />
        <span v-else class="text-muted-foreground italic">— (created)</span>
      </div>
    </div>
    <div>
      <p class="text-xs font-medium text-muted-foreground uppercase mb-2">After</p>
      <div class="rounded-lg border border-border bg-muted/30 p-3 overflow-auto max-h-64 text-xs">
        <VueJsonPretty
          v-if="newValue"
          :data="newValue"
          :deep="3"
          :show-length="true"
          :highlight-selected-node="false"
        />
        <span v-else class="text-muted-foreground italic">— (deleted)</span>
      </div>
    </div>
  </div>
  <div v-if="changedKeys.length > 0" class="mt-2 flex flex-wrap gap-1.5">
    <span class="text-xs text-muted-foreground">Changed:</span>
    <span v-for="k in changedKeys" :key="k" class="text-xs px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded font-mono">
      {{ k }}
    </span>
  </div>
</template>
