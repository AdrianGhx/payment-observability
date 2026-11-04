#!/usr/bin/env bash
#
# setup.sh - uruchamia caly stos payment-observability i czeka, az bedzie gotowy.
# Uzycie: ./scripts/setup.sh

set -euo pipefail

# Katalog glowny repo, niezaleznie od tego, skad uruchomiono skrypt
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TIMEOUT_SECONDS=120

log() {
  echo "[setup] $*"
}

fail() {
  echo "[setup] BLAD: $*" >&2
  exit 1
}

check_requirements() {
  command -v docker >/dev/null 2>&1 || fail "Nie znaleziono dockera. Zainstaluj Docker Desktop."
  docker info >/dev/null 2>&1 || fail "Silnik Dockera nie dziala. Uruchom Docker Desktop."
  docker compose version >/dev/null 2>&1 || fail "Brak polecenia 'docker compose'."
  command -v curl >/dev/null 2>&1 || fail "Nie znaleziono curl."
  log "Docker OK"
}

ensure_env_file() {
  if [[ -f .env ]]; then
    log "Plik .env istnieje"
  else
    log "Brak pliku .env, generuje losowe haslo do Grafany"
    echo "GRAFANA_ADMIN_PASSWORD='$(openssl rand -base64 18)'" > .env
  fi
}

wait_for() {
  local name=$1
  local url=$2
  local deadline=$((SECONDS + TIMEOUT_SECONDS))

  until curl -sf -o /dev/null "$url"; do
    if (( SECONDS >= deadline )); then
      fail "$name nie odpowiada po ${TIMEOUT_SECONDS}s ($url). Sprawdz: docker compose logs"
    fi
    sleep 2
  done
  log "$name OK"
}

main() {
  check_requirements
  ensure_env_file

  log "Uruchamiam stos..."
  docker compose up -d --build

  wait_for "payments" "http://127.0.0.1:8000/health"
  wait_for "VictoriaMetrics" "http://127.0.0.1:8428/health"
  wait_for "vmagent" "http://127.0.0.1:8429/health"
  wait_for "Grafana" "http://127.0.0.1:3000/api/health"

  echo
  log "Gotowe! Wszystkie serwisy dzialaja."
  log "  Grafana:          http://localhost:3000  (login: admin, haslo w pliku .env)"
  log "  vmui:             http://localhost:8428/vmui"
  log "  Cele vmagenta:    http://localhost:8429/targets"
  log "  API payments:     http://localhost:8000/docs"
}

main "$@"
