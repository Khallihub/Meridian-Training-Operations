import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Lazy-loaded page components
const LoginPage = () => import('@/pages/auth/LoginPage.vue')
const ChangePasswordPage = () => import('@/pages/auth/ChangePasswordPage.vue')

// Admin
const AdminDashboard = () => import('@/pages/admin/AdminDashboard.vue')
const UserListPage = () => import('@/pages/admin/UserListPage.vue')
const UserFormPage = () => import('@/pages/admin/UserFormPage.vue')
const LocationListPage = () => import('@/pages/admin/LocationListPage.vue')
const CourseListPage = () => import('@/pages/admin/CourseListPage.vue')
const InstructorListPage = () => import('@/pages/admin/InstructorListPage.vue')
const AuditLogPage = () => import('@/pages/admin/AuditLogPage.vue')
const PolicySettingsPage = () => import('@/pages/admin/PolicySettingsPage.vue')

// Shared
const SessionListPage = () => import('@/pages/sessions/SessionListPage.vue')
const SessionFormPage = () => import('@/pages/sessions/SessionFormPage.vue')
const SessionDetailPage = () => import('@/pages/sessions/SessionDetailPage.vue')
const AttendanceManagePage = () => import('@/pages/sessions/AttendanceManagePage.vue')
const BookingListPage = () => import('@/pages/bookings/BookingListPage.vue')
const AdvancedSearchPage = () => import('@/pages/search/AdvancedSearchPage.vue')
const JobMonitorPage = () => import('@/pages/jobs/JobMonitorPage.vue')
const MonitoringPage = () => import('@/pages/jobs/MonitoringPage.vue')
const PromotionListPage = () => import('@/pages/promotions/PromotionListPage.vue')
const PromotionFormPage = () => import('@/pages/promotions/PromotionFormPage.vue')

// Learner
const LearnerDashboard = () => import('@/pages/learner/LearnerDashboard.vue')
const SessionBrowsePage = () => import('@/pages/learner/SessionBrowsePage.vue')
const CheckoutPage = () => import('@/pages/learner/CheckoutPage.vue')
const OrderReceiptPage = () => import('@/pages/learner/OrderReceiptPage.vue')

// Instructor
const InstructorDashboard = () => import('@/pages/instructor/InstructorDashboard.vue')

// Finance
const FinanceDashboard = () => import('@/pages/finance/FinanceDashboard.vue')
const OrderListPage = () => import('@/pages/finance/OrderListPage.vue')
const PaymentListPage = () => import('@/pages/finance/PaymentListPage.vue')
const RefundListPage = () => import('@/pages/finance/RefundListPage.vue')
const ReconciliationPage = () => import('@/pages/finance/ReconciliationPage.vue')

// DataOps
const DataOpsDashboard = () => import('@/pages/dataops/DataOpsDashboard.vue')
const IngestionSourceListPage = () => import('@/pages/dataops/IngestionSourceListPage.vue')
const IngestionSourceFormPage = () => import('@/pages/dataops/IngestionSourceFormPage.vue')
const IngestionSourceDetailPage = () => import('@/pages/dataops/IngestionSourceDetailPage.vue')

// Misc
const NotFoundPage = () => import('@/pages/NotFoundPage.vue')
const ForbiddenPage = () => import('@/pages/ForbiddenPage.vue')

const ROLE_HOME: Record<string, string> = {
  admin: '/admin/dashboard',
  instructor: '/instructor/dashboard',
  learner: '/learner/dashboard',
  finance: '/finance/dashboard',
  dataops: '/dataops/dashboard',
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // Auth (no layout guard)
    { path: '/login', component: LoginPage, meta: { public: true } },
    { path: '/change-password', component: ChangePasswordPage, meta: { roles: ['admin', 'instructor', 'learner', 'finance', 'dataops'] } },

    // Root redirect
    { path: '/', redirect: () => {
      const auth = useAuthStore()
      return ROLE_HOME[auth.role ?? ''] ?? '/login'
    }},

    // Admin
    { path: '/admin/dashboard', component: AdminDashboard, meta: { roles: ['admin'] } },
    { path: '/admin/sessions', component: SessionListPage, meta: { roles: ['admin'] } },
    { path: '/admin/sessions/new', component: SessionFormPage, meta: { roles: ['admin'] } },
    { path: '/admin/sessions/:id', component: SessionDetailPage, meta: { roles: ['admin'] } },
    { path: '/admin/sessions/:id/edit', component: SessionFormPage, meta: { roles: ['admin'] } },
    { path: '/admin/bookings', component: BookingListPage, meta: { roles: ['admin'] } },
    { path: '/admin/users', component: UserListPage, meta: { roles: ['admin'] } },
    { path: '/admin/users/new', component: UserFormPage, meta: { roles: ['admin'] } },
    { path: '/admin/users/:id', component: UserFormPage, meta: { roles: ['admin'] } },
    { path: '/admin/locations', component: LocationListPage, meta: { roles: ['admin'] } },
    { path: '/admin/courses', component: CourseListPage, meta: { roles: ['admin'] } },
    { path: '/admin/instructors', component: InstructorListPage, meta: { roles: ['admin'] } },
    { path: '/admin/promotions', component: PromotionListPage, meta: { roles: ['admin'] } },
    { path: '/admin/promotions/new', component: PromotionFormPage, meta: { roles: ['admin'] } },
    { path: '/admin/promotions/:id/edit', component: PromotionFormPage, meta: { roles: ['admin'] } },
    { path: '/admin/search', component: AdvancedSearchPage, meta: { roles: ['admin'] } },
    { path: '/admin/audit-logs', component: AuditLogPage, meta: { roles: ['admin'] } },
    { path: '/admin/jobs', component: JobMonitorPage, meta: { roles: ['admin'] } },
    { path: '/admin/monitoring', component: MonitoringPage, meta: { roles: ['admin'] } },
    { path: '/admin/policy', component: PolicySettingsPage, meta: { roles: ['admin'] } },

    // Instructor
    { path: '/instructor/dashboard', component: InstructorDashboard, meta: { roles: ['instructor'] } },
    { path: '/instructor/sessions', component: SessionListPage, meta: { roles: ['instructor'] } },
    { path: '/instructor/sessions/:id', component: SessionDetailPage, meta: { roles: ['instructor'] } },
    { path: '/instructor/sessions/:id/attendance', component: AttendanceManagePage, meta: { roles: ['instructor'] } },
    { path: '/instructor/bookings', component: BookingListPage, meta: { roles: ['instructor'] } },
    { path: '/instructor/search', component: AdvancedSearchPage, meta: { roles: ['instructor'] } },

    // Learner
    { path: '/learner/dashboard', component: LearnerDashboard, meta: { roles: ['learner'] } },
    { path: '/learner/sessions', component: SessionBrowsePage, meta: { roles: ['learner'] } },
    { path: '/learner/sessions/:id', component: SessionDetailPage, meta: { roles: ['learner'] } },
    { path: '/learner/bookings', component: BookingListPage, meta: { roles: ['learner'] } },
    { path: '/learner/checkout', component: CheckoutPage, meta: { roles: ['learner'] } },
    { path: '/learner/orders/:id', component: OrderReceiptPage, meta: { roles: ['learner'] } },

    // Finance
    { path: '/finance/dashboard', component: FinanceDashboard, meta: { roles: ['finance'] } },
    { path: '/finance/orders', component: OrderListPage, meta: { roles: ['finance'] } },
    { path: '/finance/payments', component: PaymentListPage, meta: { roles: ['finance'] } },
    { path: '/finance/refunds', component: RefundListPage, meta: { roles: ['finance'] } },
    { path: '/finance/reconciliation', component: ReconciliationPage, meta: { roles: ['finance'] } },
    { path: '/finance/promotions', component: PromotionListPage, meta: { roles: ['finance'] } },
    { path: '/finance/promotions/new', component: PromotionFormPage, meta: { roles: ['finance'] } },
    { path: '/finance/search', component: AdvancedSearchPage, meta: { roles: ['finance'] } },

    // DataOps
    { path: '/dataops/dashboard', component: DataOpsDashboard, meta: { roles: ['dataops'] } },
    { path: '/dataops/ingestion', component: IngestionSourceListPage, meta: { roles: ['dataops'] } },
    { path: '/dataops/ingestion/new', component: IngestionSourceFormPage, meta: { roles: ['dataops'] } },
    { path: '/dataops/ingestion/:id', component: IngestionSourceDetailPage, meta: { roles: ['dataops'] } },
    { path: '/dataops/jobs', component: JobMonitorPage, meta: { roles: ['dataops'] } },
    { path: '/dataops/monitoring', component: MonitoringPage, meta: { roles: ['dataops'] } },

    // Errors
    { path: '/403', component: ForbiddenPage, meta: { public: true } },
    { path: '/:pathMatch(.*)*', component: NotFoundPage, meta: { public: true } },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  if (to.meta.public) return next()

  // Try to restore session if we have a stored refresh token
  if (!auth.isAuthenticated) {
    await auth.restoreSession()
  }

  if (!auth.isAuthenticated) return next('/login')

  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && !allowedRoles.includes(auth.role!)) {
    return next('/403')
  }

  next()
})

export default router
