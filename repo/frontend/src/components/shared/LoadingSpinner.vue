<script setup lang="ts">
defineProps<{ size?: 'sm' | 'md' | 'lg' }>()
</script>

<template>
  <div class="flex items-center justify-center">
    <div
      :class="[
        'border-2 border-primary border-t-transparent rounded-full animate-spin',
        size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-10 w-10' : 'h-6 w-6'
      ]"
    />
  </div>
</template>
