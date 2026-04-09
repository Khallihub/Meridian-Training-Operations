import { defineStore } from 'pinia'
import { ref } from 'vue'
import { jobsApi } from '@/api/endpoints/jobs'

export interface JobStat {
  job_name: string
  total_executions: number
  success_count: number
  failure_count: number
  success_rate_pct: number
  avg_duration_ms: number
  p95_duration_ms: number
  last_run_at: string | null
  last_status: 'success' | 'failure' | null
}

export interface JobExecution {
  id: string
  job_name: string
  started_at: string
  finished_at: string | null
  status: 'success' | 'failure' | 'late'
  error_detail: string | null
}

export interface Alert {
  id: string
  type: string
  message: string
  job_name: string | null
  created_at: string
}

export const useJobsStore = defineStore('jobs', () => {
  const stats = ref<{ window_minutes: number; jobs: JobStat[] } | null>(null)
  const executions = ref<JobExecution[]>([])
  const alerts = ref<Alert[]>([])
  const health = ref<{ status: string; timestamp: string } | null>(null)
  const loading = ref(false)

  async function fetchStats(windowMinutes = 60) {
    loading.value = true
    try {
      stats.value = await jobsApi.getStats(windowMinutes)
    } finally {
      loading.value = false
    }
  }

  async function fetchExecutions(jobName: string) {
    executions.value = await jobsApi.getExecutions(jobName)
  }

  async function fetchAlerts() {
    alerts.value = await jobsApi.getAlerts()
  }

  async function fetchHealth() {
    health.value = await jobsApi.getHealth()
  }

  const triggering = ref<string | null>(null)

  async function triggerJob(jobName: string) {
    triggering.value = jobName
    try {
      await jobsApi.triggerJob(jobName)
      setTimeout(() => fetchStats(60), 2000)
    } finally {
      triggering.value = null
    }
  }

  return { stats, executions, alerts, health, loading, triggering, fetchStats, fetchExecutions, fetchAlerts, fetchHealth, triggerJob }
})
