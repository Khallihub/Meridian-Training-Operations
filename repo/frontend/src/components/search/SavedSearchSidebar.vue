<script setup lang="ts">
import { onMounted } from 'vue'
import { useSearchStore, type SavedSearch, type SearchFilters } from '@/stores/search'
import { useUiStore } from '@/stores/ui'
import { Bookmark, Trash2 } from 'lucide-vue-next'

const emit = defineEmits<{ (e: 'load', filters: SearchFilters): void }>()
const search = useSearchStore()
const ui = useUiStore()

onMounted(() => { search.fetchSaved() })

async function handleDelete(s: SavedSearch, event: Event) {
  event.stopPropagation()
  try {
    await search.deleteSearch(s.id)
    ui.addToast('Saved search deleted', 'info')
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
}
</script>

<template>
  <div class="flex flex-col gap-1">
    <h3 class="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-2 mb-1">
      Saved Searches
      <span class="ml-1 text-muted-foreground font-normal">({{ search.savedSearches.length }}/20)</span>
    </h3>

    <div v-if="search.savedSearches.length === 0" class="px-2 text-xs text-muted-foreground py-2">
      No saved searches yet.
    </div>

    <button
      v-for="s in search.savedSearches"
      :key="s.id"
      @click="emit('load', s.filters_json)"
      class="group flex items-center justify-between px-2 py-1.5 rounded text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors text-left"
    >
      <div class="flex items-center gap-2 min-w-0">
        <Bookmark class="h-3.5 w-3.5 shrink-0" />
        <span class="truncate">{{ s.name }}</span>
      </div>
      <button
        @click="handleDelete(s, $event)"
        class="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:text-destructive transition-all"
      >
        <Trash2 class="h-3.5 w-3.5" />
      </button>
    </button>
  </div>
</template>
