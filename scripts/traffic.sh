#!/usr/bin/env bash
#
# traffic.sh - generator ruchu (platnosci) do serwisu payments
# Uzycie: ./scripts/traffic.sh [-r RPS] [-d SEKUNDY] [-u URL] [-h]

set -euo pipefail

URL="http://127.0.0.1:8000"
CURRENCIES=( PLN EUR USD )
RATE=5
DURATION=30

RESULTS_FILE=$(mktemp)
trap 'rm -f "$RESULTS_FILE"' EXIT

usage() {
  cat <<USAGE
Uzycie: $(basename "$0") [-r RPS] [-d SEKUNDY] [-u URL] [-h]

  -r RPS       docelowa liczba platnosci na sekunde (domyslnie: $RATE)
  -d SEKUNDY   czas trwania w sekundach (domyslnie: $DURATION)
  -u URL       adres serwisu payments (domyslnie: $URL)
  -h           ta pomoc
USAGE
}

fail() {
  echo "[traffic] BLAD: $*" >&2
  exit 1
}

parse_args() {
  while getopts ":r:d:u:h" opt; do
    case "$opt" in
      r) RATE=$OPTARG ;;
      d) DURATION=$OPTARG ;;
      u) URL=$OPTARG ;;
      h) usage; exit 0 ;;
      :) fail "Opcja -$OPTARG wymaga wartosci (uzyj -h)" ;;
      \?) fail "Nieznana opcja -$OPTARG (uzyj -h)" ;;
    esac
  done

  [[ $RATE =~ ^[1-9][0-9]*$ ]] || fail "RPS musi byc dodatnia liczba calkowita, podano: $RATE"
  [[ $DURATION =~ ^[1-9][0-9]*$ ]] || fail "Czas musi byc dodatnia liczba calkowita, podano: $DURATION"
}

send_payment() {
  local index=$(( RANDOM % ${#CURRENCIES[@]} ))
  local currency=${CURRENCIES[$index]}
  local amount=$(( RANDOM % 1000 + 1 ))

  curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 \
    -X POST "$URL/payments" \
    -H "Content-Type: application/json" \
    -d "{\"amount\": $amount, \"currency\": \"$currency\"}" || true
}

print_summary() {
  local total errors
  total=$(wc -l < "$RESULTS_FILE" | tr -d ' ')

  echo
  echo "[traffic] Wyslano: $total"
  if (( total == 0 )); then
    echo "[traffic] Brak wyslanych platnosci"
    return
  fi

  awk -v t="$total" -v d="$DURATION" -v r="$RATE" \
    'BEGIN { printf "[traffic] Rzeczywiste tempo: %.1f platnosci/s (cel: %s)\n", t / d, r }'
  sort "$RESULTS_FILE" | uniq -c | while read -r count code; do
    echo "[traffic]   HTTP $code: $count"
  done
  errors=$(grep -cv '^2' "$RESULTS_FILE" || true)
  awk -v e="$errors" -v t="$total" \
    'BEGIN { printf "[traffic] Bledy (nie-2xx): %d (%.1f%%)\n", e, 100 * e / t }'
}

main() {
  parse_args "$@"

  curl -sf -o /dev/null --max-time 3 "$URL/health" \
    || fail "Serwis nie odpowiada pod $URL/health. Uruchom ./scripts/setup.sh"

  local interval end
  interval=$(awk -v r="$RATE" 'BEGIN { printf "%.3f", 1 / r }')
  end=$(( SECONDS + DURATION ))

  echo "[traffic] Cel: $RATE platnosci/s przez ${DURATION}s do $URL"
  while (( SECONDS < end )); do
    send_payment >> "$RESULTS_FILE"
    printf "."
    sleep "$interval"
  done

  print_summary
}

main "$@"
