#!/usr/bin/env bash
# Shared helpers to start/stop demo API + dashboard as detached daemons.
# Sourced by seed_demo.sh and start_demo.sh — do not run directly.

demo_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  echo "$here"
}

demo_run_dir() {
  local dir
  dir="$(demo_root)/.run"
  mkdir -p "$dir"
  echo "$dir"
}

demo_api_port() { echo "${API_PORT:-8000}"; }
demo_web_port() { echo "${WEB_PORT:-5173}"; }

demo_cors_origins() {
  local p
  p="$(demo_web_port)"
  echo "http://localhost:${p},http://127.0.0.1:${p},http://localhost:5174,http://127.0.0.1:5174"
}

demo_backend_pid_file() { echo "$(demo_run_dir)/demo-backend.pid"; }
demo_backend_log() { echo "$(demo_run_dir)/demo-backend.log"; }
demo_dashboard_pid_file() { echo "$(demo_run_dir)/demo-dashboard.pid"; }
demo_dashboard_log() { echo "$(demo_run_dir)/demo-dashboard.log"; }

demo_pid_alive() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

demo_stop_pidfile() {
  local pid_file="$1"
  local label="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if demo_pid_alive "$pid"; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      demo_pid_alive "$pid" && kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi
  # Fallback: kill orphaned matchers (seed_demo legacy)
  case "$label" in
    backend) pkill -f "uvicorn app.main:app --port $(demo_api_port)" 2>/dev/null || true ;;
    dashboard) pkill -f "vite.*$(demo_web_port)" 2>/dev/null || true ;;
  esac
}

demo_stop_all() {
  demo_stop_pidfile "$(demo_backend_pid_file)" backend
  demo_stop_pidfile "$(demo_dashboard_pid_file)" dashboard
}

demo_health_ok() {
  local url="$1"
  curl -sf --max-time 2 "$url" >/dev/null 2>&1
}

demo_ensure_docker() {
  local root backend compose
  root="$(demo_root)"
  backend="$root/backend"
  compose="docker compose -f $backend/docker-compose.yml"
  cd "$backend"
  $compose up -d postgres redis
  local i
  for i in $(seq 1 30); do
    if $compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Postgres did not become ready within 30s" >&2
  return 1
}

demo_start_backend() {
  local root backend port pid_file log_file
  root="$(demo_root)"
  backend="$root/backend"
  port="$(demo_api_port)"
  pid_file="$(demo_backend_pid_file)"
  log_file="$(demo_backend_log)"

  if demo_health_ok "http://localhost:${port}/health"; then
    return 0
  fi

  demo_stop_pidfile "$pid_file" backend

  (cd "$backend" && pip install -q -e . >/dev/null 2>&1) || true

  nohup env \
    DATABASE_URL="${DATABASE_URL:-postgresql://postgres:dev@localhost:5433/agentcogs}" \
    REDIS_URL="${REDIS_URL:-redis://localhost:6379}" \
    JWT_SECRET="${JWT_SECRET:-demo-secret}" \
    CORS_ORIGINS="$(demo_cors_origins)" \
    ENVIRONMENT="${ENVIRONMENT:-development}" \
    DEMO_ENABLED="${DEMO_ENABLED:-1}" \
    uvicorn app.main:app --port "$port" --log-level warning \
    >>"$log_file" 2>&1 </dev/null &
  echo $! >"$pid_file"
  disown 2>/dev/null || true

  local i
  for i in $(seq 1 20); do
    if demo_health_ok "http://localhost:${port}/health"; then
      return 0
    fi
    sleep 1
  done

  echo "Backend failed to start. Log: $log_file" >&2
  tail -20 "$log_file" >&2 2>/dev/null || true
  return 1
}

demo_start_dashboard() {
  local root port pid_file log_file
  root="$(demo_root)"
  port="$(demo_web_port)"
  pid_file="$(demo_dashboard_pid_file)"
  log_file="$(demo_dashboard_log)"

  if demo_health_ok "http://127.0.0.1:${port}/"; then
    return 0
  fi

  demo_stop_pidfile "$pid_file" dashboard

  nohup npm run dev -- --host 127.0.0.1 --port "$port" --strictPort \
    >>"$log_file" 2>&1 </dev/null &
  echo $! >"$pid_file"
  disown 2>/dev/null || true

  local i
  for i in $(seq 1 30); do
    if demo_health_ok "http://127.0.0.1:${port}/"; then
      return 0
    fi
    sleep 1
  done

  echo "Dashboard failed to start. Log: $log_file" >&2
  tail -20 "$log_file" >&2 2>/dev/null || true
  return 1
}

demo_print_status() {
  local port web
  port="$(demo_api_port)"
  web="$(demo_web_port)"
  echo "API:        http://localhost:${port}/health"
  echo "Dashboard:  http://localhost:${web}/demo"
  echo "Logs:       $(demo_run_dir)/"
  if [[ -f "$(demo_root)/tools/.demo_env" ]]; then
    # shellcheck disable=SC1091
    source "$(demo_root)/tools/.demo_env"
    echo "Workspace:  ${DEMO_WORKSPACE_ID:-unknown}"
  fi
}
