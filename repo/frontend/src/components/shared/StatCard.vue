<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  delta?: number
  description?: string
}>()
</script>

<template>
  <div class="bg-card border border-border rounded-lg p-5">
    <p class="text-sm text-muted-foreground">{{ label }}</p>
    <p class="text-2xl font-bold text-foreground mt-1">{{ value }}</p>
    <div v-if="delta !== undefined" :class="['flex items-center gap-1 text-xs mt-1', delta >= 0 ? 'text-green-600' : 'text-red-600']">
      <span>{{ delta >= 0 ? '▲' : '▼' }} {{ Math.abs(delta) }}%</span>
    </div>
    <p v-if="description" class="text-xs text-muted-foreground mt-1">{{ description }}</p>
  </div>
</template>
