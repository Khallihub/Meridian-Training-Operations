#!/usr/bin/env bash
# run_tests.sh — Run backend and frontend test suites inside Docker containers.
# Usage:
#   ./run_tests.sh                  # all backend + frontend tests
#   ./run_tests.sh --backend        # backend only
#   ./run_tests.sh --frontend       # frontend only
#   ./run_tests.sh tests/unit/      # backend subset by path (any pytest flag)
#   ./run_tests.sh -k test_booking  # backend subset by expression
#
# If the stack is not running this script starts it and waits for the backend
# to become healthy before executing the backend tests.  Frontend tests run in
# a one-off container built from the frontend Dockerfile's build stage (which
# has node/npm/vitest) — they do not require the full stack.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE="docker compose"
BACKEND_SERVICE="backend"
STARTUP_TIMEOUT=120   # seconds to wait for backend healthy after `up`
POLL_INTERVAL=5
FE_IMAGE="meridian-frontend-test"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[run_tests]${NC} $*"; }
warning() { echo -e "${YELLOW}[run_tests]${NC} $*"; }
error()   { echo -e "${RED}[run_tests]${NC} $*" >&2; }

# ── Parse flags ──────────────────────────────────────────────────────────────
RUN_BACKEND=true
RUN_FRONTEND=true
PYTEST_ARGS=()

if [[ "${1:-}" == "--backend" ]]; then
  RUN_FRONTEND=false
  shift
elif [[ "${1:-}" == "--frontend" ]]; then
  RUN_BACKEND=false
  shift
fi

# Remaining args are forwarded to pytest (backend only)
PYTEST_ARGS=("${@:-tests/}")

# ── Check that docker compose is available ───────────────────────────────────
if ! docker compose version &>/dev/null; then
  error "docker compose is not available. Install Docker Desktop or the compose plugin."
  exit 1
fi

EXIT_CODE=0

# ══════════════════════════════════════════════════════════════════════════════
# Backend tests
# ══════════════════════════════════════════════════════════════════════════════
if $RUN_BACKEND; then
  # ── Determine whether the backend container is already running and healthy ─
  backend_healthy() {
    $COMPOSE ps --format json "$BACKEND_SERVICE" 2>/dev/null \
      | grep -q '"Health":"healthy"'
  }

  # ── Start the stack if needed ──────────────────────────────────────────────
  if backend_healthy; then
    info "Backend container is already healthy — skipping startup."
  else
    warning "Backend is not healthy (or not running). Starting the stack..."
    $COMPOSE up -d --build

    info "Waiting for backend to become healthy (timeout: ${STARTUP_TIMEOUT}s)..."
    elapsed=0
    until backend_healthy; do
      if (( elapsed >= STARTUP_TIMEOUT )); then
        error "Backend did not become healthy within ${STARTUP_TIMEOUT}s."
        error "Check logs with:  docker compose logs backend"
        exit 1
      fi
      sleep "$POLL_INTERVAL"
      (( elapsed += POLL_INTERVAL ))
      info "  ...still waiting (${elapsed}s elapsed)"
    done
    info "Backend is healthy."
  fi

  # ── Run backend tests ──────────────────────────────────────────────────────
  info "Running backend tests: pytest ${PYTEST_ARGS[*]}"
  echo "──────────────────────────────────────────────────────────────────────────"

  set +e
  $COMPOSE exec "$BACKEND_SERVICE" pytest "${PYTEST_ARGS[@]}" -v
  BE_EXIT=$?
  set -e

  echo "──────────────────────────────────────────────────────────────────────────"
  if (( BE_EXIT == 0 )); then
    info "Backend tests passed."
  else
    error "Backend tests failed (exit code ${BE_EXIT})."
    EXIT_CODE=$BE_EXIT
  fi
fi

# ══════════════════════════════════════════════════════════════════════════════
# Frontend tests
# ══════════════════════════════════════════════════════════════════════════════
if $RUN_FRONTEND; then
  # The production frontend image is nginx (no node). Build from the
  # Dockerfile's "build" stage which has node, node_modules, and source.
  info "Building frontend test image (target: build stage)..."
  docker build --target build -t "$FE_IMAGE" ./frontend -q

  info "Running frontend tests: vitest run"
  echo "──────────────────────────────────────────────────────────────────────────"

  set +e
  docker run --rm "$FE_IMAGE" npm run test
  FE_EXIT=$?
  set -e

  echo "──────────────────────────────────────────────────────────────────────────"
  if (( FE_EXIT == 0 )); then
    info "Frontend tests passed."
  else
    error "Frontend tests failed (exit code ${FE_EXIT})."
    if (( EXIT_CODE == 0 )); then EXIT_CODE=$FE_EXIT; fi
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
if (( EXIT_CODE == 0 )); then
  info "All tests passed."
else
  error "Some tests failed."
fi

exit "$EXIT_CODE"
