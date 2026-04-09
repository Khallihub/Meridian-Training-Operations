<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useIngestionStore } from '@/stores/ingestion'
import { useUiStore } from '@/stores/ui'
import AppLayout from '@/layouts/AppLayout.vue'

const router = useRouter()
const ingestion = useIngestionStore()
const ui = useUiStore()

const form = ref({
  name: '',
  type: 'kafka' as const,
  collection_frequency_seconds: 60,
  concurrency_cap: 4,
  is_active: true,
  config: '{}',
})
const isSubmitting = ref(false)
const configError = ref('')

function validateConfig() {
  try { JSON.parse(form.value.config); configError.value = ''; return true }
  catch { configError.value = 'Invalid JSON'; return false }
}

async function handleSubmit() {
  if (!validateConfig()) return
  isSubmitting.value = true
  try {
    const source = await ingestion.createSource({
      ...form.value,
      config: JSON.parse(form.value.config),
    })
    // Test connection immediately
    try {
      const test = await ingestion.testConnection(source.id)
      ui.addToast(test.success ? `Source created & connected (${test.latency_ms}ms)` : `Source created but connection test failed: ${test.error}`, test.success ? 'success' : 'warning')
    } catch { ui.addToast('Source created', 'success') }
    router.push(`/dataops/ingestion/${source.id}`)
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="max-w-2xl">
      <h1 class="text-xl font-semibold text-foreground mb-6">New Ingestion Source</h1>
      <div class="bg-card border border-border rounded-lg p-6">
        <form @submit.prevent="handleSubmit" class="flex flex-col gap-5">
          <div>
            <label class="block text-sm font-medium mb-1">Name</label>
            <input v-model="form.name" required class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Type</label>
            <select v-model="form.type" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm">
              <option value="kafka">Kafka</option>
              <option value="logstash">Logstash (HTTP push)</option>
              <option value="flume">Flume (HTTP push)</option>
              <option value="batch_file">Batch File</option>
              <option value="cdc_mysql">CDC MySQL</option>
              <option value="cdc_pg">CDC PostgreSQL</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Frequency (sec)</label>
              <input v-model.number="form.collection_frequency_seconds" type="number" min="1" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Concurrency Cap</label>
              <input v-model.number="form.concurrency_cap" type="number" min="1" max="20" class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm" />
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Config (JSON)</label>
            <textarea
              v-model="form.config"
              rows="6"
              class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm font-mono"
              :class="configError ? 'border-destructive' : ''"
              placeholder='{"bootstrap_servers": "kafka:9092", "topic": "events"}'
            />
            <p v-if="configError" class="text-xs text-destructive mt-1">{{ configError }}</p>
            <p class="text-xs text-muted-foreground mt-1">Config values are encrypted at rest on the backend.</p>
          </div>
          <div class="flex items-center gap-2">
            <input id="active" type="checkbox" v-model="form.is_active" class="rounded" />
            <label for="active" class="text-sm">Active</label>
          </div>
          <div class="flex gap-3 pt-2">
            <button type="submit" :disabled="isSubmitting" class="px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90 disabled:opacity-50 flex items-center gap-2">
              <div v-if="isSubmitting" class="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
              Save & Test Connection
            </button>
            <button type="button" @click="router.back()" class="px-4 py-2 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>
