<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useSearchStore, type SearchFilters } from '@/stores/search'
import { useUiStore } from '@/stores/ui'
import { useExport } from '@/composables/useExport'
import AppLayout from '@/layouts/AppLayout.vue'
import SavedSearchSidebar from '@/components/search/SavedSearchSidebar.vue'
import DataTable from '@/components/tables/DataTable.vue'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import { Search, Download, Bookmark, AlertTriangle } from 'lucide-vue-next'
import { formatInTimeZone } from 'date-fns-tz'
import { parseISO } from 'date-fns'

const searchStore = useSearchStore()
const ui = useUiStore()
const { exporting, exportSearch } = useExport()

const filters = reactive<SearchFilters & { include_facets: boolean }>({
  invoice_number: '',
  learner_phone: '',
  enrollment_status: '',
  date_from: '',
  date_to: '',
  site_id: '',
  instructor_id: '',
  page: 1,
  page_size: 25,
  include_facets: true,
})

const saveNamePrompt = ref(false)
const saveName = ref('')
const isSearching = ref(false)

const columns = [
  { key: 'booking_id', label: 'Booking ID' },
  { key: 'learner_username', label: 'Learner' },
  { key: 'learner_phone_masked', label: 'Phone' },
  { key: 'session_title', label: 'Session' },
  { key: 'session_date', label: 'Date' },
  { key: 'site_name', label: 'Site' },
  { key: 'status', label: 'Status' },
  { key: 'amount', label: 'Amount' },
]

async function runSearch() {
  isSearching.value = true
  try {
    await searchStore.runSearch(filters, true)
  } finally {
    isSearching.value = false
  }
}

// Facet pill click — add to filter and re-run
function applyFacet(field: string, value: string) {
  if (field === 'enrollment_status') {
    filters.enrollment_status = filters.enrollment_status === value ? '' : value
  } else if (field === 'site_id') {
    filters.site_id = filters.site_id === value ? '' : value
  } else if (field === 'instructor_id') {
    filters.instructor_id = filters.instructor_id === value ? '' : value
  }
  runSearch()
}

function loadSaved(savedFilters: SearchFilters) {
  Object.assign(filters, savedFilters)
  runSearch()
}

async function handleSave() {
  if (!saveName.value.trim()) return
  try {
    await searchStore.saveSearch(saveName.value.trim(), { ...filters })
    ui.addToast(`Search "${saveName.value}" saved`, 'success')
    saveNamePrompt.value = false
    saveName.value = ''
  } catch (e: any) {
    ui.addToast(e.message, 'error')
  }
}

function handleExport(format: 'csv' | 'xlsx') {
  exportSearch({ ...filters }, format)
}

const tz = Intl.DateTimeFormat().resolvedOptions().timeZone

function fmt(n: number | null | undefined) {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

function fmtDate(v: unknown) {
  if (!v) return '—'
  try { return formatInTimeZone(parseISO(String(v)), tz, 'MMM d, yyyy h:mm a') }
  catch { return String(v) }
}
</script>

<template>
  <AppLayout>
    <div class="flex gap-6 h-full">
      <!-- Sidebar: saved searches — correction #2 -->
      <aside class="w-52 shrink-0">
        <SavedSearchSidebar @load="loadSaved" />
      </aside>

      <!-- Main -->
      <div class="flex-1 min-w-0 flex flex-col gap-5">
        <h1 class="text-xl font-semibold text-foreground">Advanced Search</h1>

        <!-- Search panel -->
        <div class="bg-card border border-border rounded-lg p-5">
          <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label class="block text-xs text-muted-foreground mb-1">Invoice / Order ID</label>
              <input v-model="filters.invoice_number" type="text" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" />
            </div>
            <div>
              <label class="block text-xs text-muted-foreground mb-1">Learner Phone</label>
              <input v-model="filters.learner_phone" type="text" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" />
            </div>
            <div>
              <label class="block text-xs text-muted-foreground mb-1">Status</label>
              <select v-model="filters.enrollment_status" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm">
                <option value="">All</option>
                <option>requested</option>
                <option>confirmed</option>
                <option>rescheduled_out</option>
                <option>canceled</option>
                <option>completed</option>
                <option>no_show</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-muted-foreground mb-1">Date From</label>
              <input v-model="filters.date_from" type="date" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" />
            </div>
            <div>
              <label class="block text-xs text-muted-foreground mb-1">Date To</label>
              <input v-model="filters.date_to" type="date" class="w-full px-2 py-1.5 rounded border border-border bg-background text-sm" />
            </div>
          </div>

          <div class="flex flex-wrap gap-2">
            <button @click="runSearch" :disabled="isSearching" class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded text-sm hover:opacity-90 disabled:opacity-50">
              <Search class="h-4 w-4" />
              {{ isSearching ? 'Searching…' : 'Search' }}
            </button>

            <!-- Save search -->
            <button @click="saveNamePrompt = !saveNamePrompt" class="flex items-center gap-2 px-3 py-2 bg-secondary text-secondary-foreground rounded text-sm hover:bg-accent">
              <Bookmark class="h-4 w-4" /> Save
            </button>

            <!-- Export buttons — correction #2: disabled + tooltip when >50k rows -->
            <div class="relative group">
              <button
                @click="!searchStore.exportDisabled && handleExport('csv')"
                :disabled="exporting || searchStore.exportDisabled"
                :class="['flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors', searchStore.exportDisabled ? 'bg-muted text-muted-foreground cursor-not-allowed' : 'bg-secondary text-secondary-foreground hover:bg-accent']"
              >
                <Download class="h-4 w-4" /> CSV
                <AlertTriangle v-if="searchStore.exportDisabled" class="h-3.5 w-3.5 text-yellow-500" />
              </button>
              <div v-if="searchStore.exportDisabled" class="absolute bottom-full left-0 mb-1 w-56 p-2 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none z-10">
                Export disabled: result set exceeds 50,000 rows. Narrow your filters first.
              </div>
            </div>

            <div class="relative group">
              <button
                @click="!searchStore.exportDisabled && handleExport('xlsx')"
                :disabled="exporting || searchStore.exportDisabled"
                :class="['flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors', searchStore.exportDisabled ? 'bg-muted text-muted-foreground cursor-not-allowed' : 'bg-secondary text-secondary-foreground hover:bg-accent']"
              >
                <Download class="h-4 w-4" /> Excel
                <AlertTriangle v-if="searchStore.exportDisabled" class="h-3.5 w-3.5 text-yellow-500" />
              </button>
            </div>
          </div>

          <!-- Save name prompt -->
          <div v-if="saveNamePrompt" class="mt-3 flex gap-2">
            <input v-model="saveName" type="text" placeholder="Search name…" class="flex-1 px-2 py-1.5 rounded border border-border bg-background text-sm" @keydown.enter="handleSave" />
            <button @click="handleSave" class="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Save</button>
            <button @click="saveNamePrompt = false" class="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm">Cancel</button>
          </div>
        </div>

        <!-- Facet pills — correction #2 -->
        <div v-if="searchStore.facets" class="flex flex-wrap gap-3 text-sm">
          <!-- Status facets -->
          <div class="flex flex-wrap gap-1.5 items-center">
            <span class="text-xs text-muted-foreground font-medium">Status:</span>
            <button
              v-for="(count, status) in searchStore.facets.enrollment_status"
              :key="status"
              @click="applyFacet('enrollment_status', status)"
              :class="['px-2 py-0.5 rounded-full text-xs border transition-colors', filters.enrollment_status === status ? 'bg-primary text-primary-foreground border-primary' : 'bg-secondary text-secondary-foreground border-border hover:border-primary']"
            >
              {{ status }} ({{ count }})
            </button>
          </div>

          <!-- Site facets -->
          <div v-if="searchStore.facets.site.length" class="flex flex-wrap gap-1.5 items-center">
            <span class="text-xs text-muted-foreground font-medium">Site:</span>
            <button
              v-for="site in searchStore.facets.site"
              :key="site.id"
              @click="applyFacet('site_id', site.id)"
              :class="['px-2 py-0.5 rounded-full text-xs border transition-colors', filters.site_id === site.id ? 'bg-primary text-primary-foreground border-primary' : 'bg-secondary text-secondary-foreground border-border hover:border-primary']"
            >
              {{ site.name }} ({{ site.count }})
            </button>
          </div>

          <!-- Instructor facets -->
          <div v-if="searchStore.facets.instructor.length" class="flex flex-wrap gap-1.5 items-center">
            <span class="text-xs text-muted-foreground font-medium">Instructor:</span>
            <button
              v-for="instr in searchStore.facets.instructor"
              :key="instr.id"
              @click="applyFacet('instructor_id', instr.id)"
              :class="['px-2 py-0.5 rounded-full text-xs border transition-colors', filters.instructor_id === instr.id ? 'bg-primary text-primary-foreground border-primary' : 'bg-secondary text-secondary-foreground border-border hover:border-primary']"
            >
              {{ instr.name }} ({{ instr.count }})
            </button>
          </div>
        </div>

        <!-- Results info -->
        <div v-if="searchStore.totalCount > 0" class="text-xs text-muted-foreground">
          {{ searchStore.totalCount.toLocaleString() }} results · {{ searchStore.queryTimeMs }}ms
          <span v-if="searchStore.exportDisabled" class="ml-2 text-yellow-600 dark:text-yellow-400 font-medium">
            ⚠ Too many results to export (max 50k). Add filters to enable export.
          </span>
        </div>

        <!-- Results table -->
        <DataTable
          :columns="columns"
          :rows="(searchStore.results as any[])"
          :loading="isSearching"
          :total-count="searchStore.totalCount"
          :page-size="filters.page_size!"
          :current-page="filters.page!"
          @page-change="(p) => { filters.page = p; runSearch() }"
          @size-change="(s) => { filters.page_size = s; filters.page = 1; runSearch() }"
          empty-title="No results"
          empty-description="Try adjusting your search filters"
        >
          <template #cell-session_date="{ value }">
            {{ fmtDate(value) }}
          </template>
          <template #cell-status="{ value }">
            <StatusBadge :status="String(value)" />
          </template>
          <template #cell-amount="{ value }">
            {{ fmt(value as number | null) }}
          </template>
        </DataTable>
      </div>
    </div>
  </AppLayout>
</template>
