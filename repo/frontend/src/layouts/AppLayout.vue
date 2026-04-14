<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useJobsStore } from '@/stores/jobs'
import {
  Sun, Moon, Bell, ChevronLeft, ChevronRight, LogOut, Key,
  LayoutDashboard, Calendar, BookOpen, Users, MapPin, BookMarked,
  Tag, Search, ClipboardList, Briefcase, Activity, Database, Cpu, GraduationCap
} from 'lucide-vue-next'
import ToastContainer from '@/components/shared/ToastContainer.vue'

const auth = useAuthStore()
const ui = useUiStore()
const jobs = useJobsStore()
const router = useRouter()
const route = useRoute()

const alertCount = computed(() => jobs.alerts.length)

onMounted(() => {
  // Alerts are only meaningful for admin and dataops — they are the only roles
  // with a monitoring page and the alert bell in the header. Polling for other
  // roles makes unnecessary API calls and may hit authorization errors.
  if (auth.role === 'admin' || auth.role === 'dataops') {
    jobs.fetchAlerts()
    setInterval(() => jobs.fetchAlerts(), 60000)
  }
})

const navItems = computed(() => {
  const role = auth.role
  const base: Array<{ label: string; to: string; icon: unknown }> = []

  if (role === 'admin') {
    base.push(
      { label: 'Dashboard', to: '/admin/dashboard', icon: LayoutDashboard },
      { label: 'Sessions', to: '/admin/sessions', icon: Calendar },
      { label: 'Bookings', to: '/admin/bookings', icon: BookMarked },
      { label: 'Users', to: '/admin/users', icon: Users },
      { label: 'Locations', to: '/admin/locations', icon: MapPin },
      { label: 'Courses', to: '/admin/courses', icon: BookOpen },
      { label: 'Instructors', to: '/admin/instructors', icon: GraduationCap },
      { label: 'Promotions', to: '/admin/promotions', icon: Tag },
      { label: 'Search', to: '/admin/search', icon: Search },
      { label: 'Audit Logs', to: '/admin/audit-logs', icon: ClipboardList },
      { label: 'Jobs', to: '/admin/jobs', icon: Briefcase },
      { label: 'Monitoring', to: '/admin/monitoring', icon: Activity },
    )
  } else if (role === 'instructor') {
    base.push(
      { label: 'Dashboard', to: '/instructor/dashboard', icon: LayoutDashboard },
      { label: 'Sessions', to: '/instructor/sessions', icon: Calendar },
      { label: 'Bookings', to: '/instructor/bookings', icon: BookMarked },
      { label: 'Search', to: '/instructor/search', icon: Search },
    )
  } else if (role === 'learner') {
    base.push(
      { label: 'Dashboard', to: '/learner/dashboard', icon: LayoutDashboard },
      { label: 'Browse Sessions', to: '/learner/sessions', icon: Calendar },
      { label: 'My Bookings', to: '/learner/bookings', icon: BookMarked },
    )
  } else if (role === 'finance') {
    base.push(
      { label: 'Dashboard', to: '/finance/dashboard', icon: LayoutDashboard },
      { label: 'Orders', to: '/finance/orders', icon: BookOpen },
      { label: 'Payments', to: '/finance/payments', icon: Briefcase },
      { label: 'Refunds', to: '/finance/refunds', icon: Tag },
      { label: 'Reconciliation', to: '/finance/reconciliation', icon: ClipboardList },
      { label: 'Promotions', to: '/finance/promotions', icon: Tag },
      { label: 'Search', to: '/finance/search', icon: Search },
    )
  } else if (role === 'dataops') {
    base.push(
      { label: 'Dashboard', to: '/dataops/dashboard', icon: LayoutDashboard },
      { label: 'Ingestion', to: '/dataops/ingestion', icon: Database },
      { label: 'Jobs', to: '/dataops/jobs', icon: Briefcase },
      { label: 'Monitoring', to: '/dataops/monitoring', icon: Activity },
    )
  }
  return base
})

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

const userMenuOpen = ref(false)

const breadcrumb = computed(() => {
  const parts = route.path.split('/').filter(Boolean)
  return parts.map((p, i) => ({
    label: p.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    to: '/' + parts.slice(0, i + 1).join('/'),
  }))
})
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-background" @click.self="userMenuOpen = false">
    <!-- Sidebar -->
    <aside
      :class="[
        'flex flex-col border-r border-border bg-card transition-all duration-200 no-print',
        ui.sidebarCollapsed ? 'w-16' : 'w-56'
      ]"
    >
      <!-- Logo -->
      <div class="flex items-center h-14 px-3 border-b border-border shrink-0">
        <Cpu class="h-6 w-6 text-primary shrink-0" />
        <span v-if="!ui.sidebarCollapsed" class="ml-2 font-semibold text-foreground truncate">Meridian</span>
      </div>

      <!-- Nav -->
      <nav class="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-2 px-2 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          active-class="bg-accent text-foreground font-medium"
        >
          <component :is="item.icon" class="h-4 w-4 shrink-0" />
          <span v-if="!ui.sidebarCollapsed" class="truncate">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <!-- Collapse toggle -->
      <button
        @click="ui.toggleSidebar"
        class="flex items-center justify-center h-10 border-t border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      >
        <ChevronLeft v-if="!ui.sidebarCollapsed" class="h-4 w-4" />
        <ChevronRight v-else class="h-4 w-4" />
      </button>
    </aside>

    <!-- Main column -->
    <div class="flex flex-col flex-1 overflow-hidden">
      <!-- Top bar -->
      <header class="flex items-center justify-between h-14 px-4 border-b border-border bg-card shrink-0 no-print">
        <!-- Breadcrumb -->
        <nav class="flex items-center gap-1 text-sm text-muted-foreground">
          <span v-for="(crumb, i) in breadcrumb" :key="crumb.to" class="flex items-center gap-1">
            <span v-if="i > 0" class="text-border">/</span>
            <RouterLink :to="crumb.to" class="hover:text-foreground transition-colors">
              {{ crumb.label }}
            </RouterLink>
          </span>
        </nav>

        <!-- Right actions -->
        <div class="flex items-center gap-2">
          <!-- Alert bell — only admin and dataops have a monitoring page -->
          <RouterLink
            v-if="auth.role === 'admin' || auth.role === 'dataops'"
            :to="auth.role === 'dataops' ? '/dataops/monitoring' : '/admin/monitoring'"
            class="relative p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <Bell class="h-5 w-5" />
            <span v-if="alertCount > 0" class="absolute top-1 right-1 h-2 w-2 bg-destructive rounded-full" />
          </RouterLink>

          <!-- Theme toggle -->
          <button @click="ui.toggleTheme" class="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
            <Sun v-if="ui.theme === 'dark'" class="h-5 w-5" />
            <Moon v-else class="h-5 w-5" />
          </button>

          <!-- User menu -->
          <div class="relative">
            <button @click="userMenuOpen = !userMenuOpen" class="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
              <span class="font-medium">{{ auth.user?.username }}</span>
              <span class="text-xs px-1.5 py-0.5 bg-primary/10 text-primary rounded">{{ auth.role }}</span>
            </button>
            <div v-if="userMenuOpen" class="absolute right-0 top-full mt-1 w-44 bg-card border border-border rounded-md shadow-lg py-1 z-50">
              <RouterLink to="/change-password" @click="userMenuOpen = false" class="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent">
                <Key class="h-4 w-4" /> Change Password
              </RouterLink>
              <button @click="handleLogout" class="w-full flex items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-accent">
                <LogOut class="h-4 w-4" /> Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-6">
        <slot />
      </main>
    </div>

    <!-- Toast container -->
    <ToastContainer />
  </div>
</template>
