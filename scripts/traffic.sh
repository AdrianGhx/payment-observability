#!/usr/bin/env bash
#
# traffic.sh - generator ruchu (platnosci) do serwisu payments
# Uzycie: ./scripts/traffic.sh [PLATNOSCI_NA_SEKUNDE] [SEKUNDY]

set -euo pipefail

URL="http://127.0.0.1:8000"
CURRENCIES=( PLN EUR USD )
RATE=${1:-5}
DURATION=${2:-30}

RESULTS_FILE=$(mktemp)
trap 'rm -f "$RESULTS_FILE"' EXIT

send_payment() {
  local index=$(( RANDOM % ${#CURRENCIES[@]} ))
  local currency=${CURRENCIES[$index]}
  local amount=$(( RANDOM % 1000 + 1 ))

  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST "$URL/payments" \
    -H "Content-Type: application/json" \
    -d "{\"amount\": $amount, \"currency\": \"$currency\"}"
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

  awk -v t="$total" -v d="$DURATION" \
    'BEGIN { printf "[traffic] Rzeczywiste tempo: %.1f platnosci/s (cel: %s)\n", t / d, ENVIRON["RATE"] }'
  sort "$RESULTS_FILE" | uniq -c | while read -r count code; do
    echo "[traffic]   HTTP $code: $count"
  done
  errors=$(grep -cv '^2' "$RESULTS_FILE" || true)
  awk -v e="$errors" -v t="$total" \
    'BEGIN { printf "[traffic] Bledy (nie-2xx): %d (%.1f%%)\n", e, 100 * e / t }'
}

interval=$(awk -v r="$RATE" 'BEGIN { printf "%.3f", 1 / r }')
end=$(( SECONDS + DURATION ))

echo "[traffic] Cel: $RATE platnosci/s przez ${DURATION}s do $URL"
while (( SECONDS < end )); do
  send_payment >> "$RESULTS_FILE"
  printf "."
  sleep "$interval"
done

export RATE
print_summary
