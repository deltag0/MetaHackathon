#!/bin/bash
# Tier 2 verification script — tests logging + alertmanager config
set -e

BASE="http://localhost"
AM="http://localhost:9093"

echo "=== 1. Check app health through nginx ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health/live" 2>/dev/null || echo "FAIL")
echo "GET /health/live => $HTTP_CODE"

echo ""
echo "=== 2. Generate some traffic ==="
for i in $(seq 1 5); do
  curl -s -o /dev/null -w "GET /users => %{http_code}\n" "$BASE/users"
done

echo ""
echo "=== 3. Check log files exist on host ==="
for i in 1 2 3 4; do
  LOG="./logs/app-$i/app-$i.log"
  if [ -f "$LOG" ]; then
    LINES=$(wc -l < "$LOG")
    echo "  app-$i.log: $LINES lines"
  else
    echo "  app-$i.log: MISSING"
  fi
done

# Also check single-app log
if [ -f "./logs/app/app.log" ]; then
  LINES=$(wc -l < "./logs/app/app.log")
  echo "  app.log (single): $LINES lines"
fi

echo ""
echo "=== 4. Check Alertmanager status ==="
AM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$AM/-/healthy" 2>/dev/null || echo "FAIL")
echo "Alertmanager health => $AM_STATUS"

echo ""
echo "=== 5. Check Alertmanager config has real credentials ==="
AM_CONFIG=$(curl -s "$AM/api/v1/status" 2>/dev/null)
if echo "$AM_CONFIG" | grep -q "replace-with"; then
  echo "  FAIL: Alertmanager still has placeholder credentials"
elif echo "$AM_CONFIG" | grep -q "example.com"; then
  echo "  FAIL: Alertmanager still has example.com addresses"
elif echo "$AM_CONFIG" | grep -q "smtp_smarthost"; then
  echo "  OK: Alertmanager config loaded (check emails below)"
  echo "$AM_CONFIG" | python -m json.tool 2>/dev/null | grep -E "(smtp_from|smtp_smarthost|to:)" || true
else
  echo "  WARN: Could not fetch Alertmanager config"
fi

echo ""
echo "=== 6. Check Prometheus alert rules ==="
PROM_RULES=$(curl -s "http://localhost:9090/api/v1/rules" 2>/dev/null)
ALERT_COUNT=$(echo "$PROM_RULES" | python -c "import sys,json; d=json.load(sys.stdin); print(sum(len(g.get('rules',[])) for g in d.get('data',{}).get('groups',[])))" 2>/dev/null || echo "?")
echo "Prometheus has $ALERT_COUNT alert rules loaded"

echo ""
echo "=== 7. Check for any firing alerts ==="
FIRING=$(curl -s "$AM/api/v2/alerts" 2>/dev/null)
FIRING_COUNT=$(echo "$FIRING" | python -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
echo "Currently firing alerts: $FIRING_COUNT"

echo ""
echo "=== Done ==="
