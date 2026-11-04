#!/usr/bin/env bash
#
# traffic.sh - generator ruchu (platnosci) do serwisu payments
# Uzycie: ./scripts/traffic.sh [LICZBA_PLATNOSCI]

set -euo pipefail

URL="http://127.0.0.1:8000"
CURRENCIES=( PLN EUR USD )
COUNT=${1:-10}

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
  errors=$(grep -cv '^2' "$RESULTS_FILE" || true)

  echo
  echo "[traffic] Wyslano: $total"
  sort "$RESULTS_FILE" | uniq -c | while read -r count code; do
    echo "[traffic]   HTTP $code: $count"
  done
  awk -v e="$errors" -v t="$total" \
    'BEGIN { printf "[traffic] Bledy (nie-2xx): %d (%.1f%%)\n", e, 100 * e / t }'
}

echo "[traffic] Wysylam $COUNT platnosci do $URL"
for i in $(seq 1 "$COUNT"); do
  code=$(send_payment)
  printf "%3d: %s\n" "$i" "$code"
  echo "$code" >> "$RESULTS_FILE"
done

print_summary
