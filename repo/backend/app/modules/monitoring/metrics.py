"""Prometheus metrics definitions and middleware instrumentation."""

from prometheus_client import Counter, Gauge, Histogram

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route", "status_code"],
)

job_success_total = Counter(
    "job_success_total",
    "Total successful job executions",
    ["job_name"],
)

job_failure_total = Counter(
    "job_failure_total",
    "Total failed job executions",
    ["job_name"],
)

job_duration_seconds = Histogram(
    "job_duration_seconds",
    "Job execution duration in seconds",
    ["job_name"],
)

active_sessions_gauge = Gauge(
    "active_sessions_gauge",
    "Number of currently live sessions",
)

pending_orders_gauge = Gauge(
    "pending_orders_gauge",
    "Number of pending orders",
)

ingestion_rows_total = Counter(
    "ingestion_rows_total",
    "Total rows ingested",
    ["source_name"],
)
