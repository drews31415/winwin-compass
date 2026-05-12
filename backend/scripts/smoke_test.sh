#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
CURL_BIN="curl"
if command -v curl.exe >/dev/null 2>&1; then
  CURL_BIN="curl.exe"
fi

echo "=== Winwin Compass smoke test ==="
echo "BASE_URL=${BASE_URL}"

json_pretty() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool --no-ensure-ascii
  elif command -v python >/dev/null 2>&1; then
    python -m json.tool --no-ensure-ascii
  elif command -v py >/dev/null 2>&1; then
    py -m json.tool --no-ensure-ascii
  else
    cat
  fi
}

echo
echo "[1] Health"
"${CURL_BIN}" -s "${BASE_URL}/health" | json_pretty

echo
echo "[2] Area detail: 3110016"
"${CURL_BIN}" -s "${BASE_URL}/api/v1/areas/3110016" | json_pretty

echo
echo "[3] ML risk"
"${CURL_BIN}" -s "${BASE_URL}/api/v1/ml/risk/3110016" | json_pretty

echo
echo "[4] ML forecast"
"${CURL_BIN}" -s "${BASE_URL}/api/v1/ml/forecast/3110016?periods=4" | json_pretty

echo
echo "[5] Policy match"
"${CURL_BIN}" -s "${BASE_URL}/api/v1/policy/match?business_type=%EC%B9%B4%ED%8E%98&capital=5000" | json_pretty

echo
echo "[6] Chat simple"
"${CURL_BIN}" -s -X POST "${BASE_URL}/api/v1/chat/simple" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"message":"\uc885\ub85c3\uac00 \uce74\ud398 \ucc3d\uc5c5 \uc5b4\ub54c?","session_id":"smoke-test","user_context":{}}' \
  | json_pretty

echo
echo "=== Smoke test complete ==="
