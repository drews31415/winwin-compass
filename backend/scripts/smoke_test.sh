#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
CURL_BIN="curl"
if command -v curl.exe >/dev/null 2>&1; then
  CURL_BIN="curl.exe"
fi

echo "=== 골목 컴퍼스 스모크 테스트 ==="
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
echo "[1] 헬스체크"
"${CURL_BIN}" -s "${BASE_URL}/health" | json_pretty

echo
echo "[2] 상권 리포트 데이터 (종로3가)"
"${CURL_BIN}" -s "${BASE_URL}/api/v1/areas/3110016" | json_pretty

echo
echo "[3] ML 위험 점수"
"${CURL_BIN}" -s "${BASE_URL}/api/v1/ml/risk/3110016" | json_pretty

echo
echo "[4] ML 예측"
"${CURL_BIN}" -s "${BASE_URL}/api/v1/ml/forecast/3110016?periods=4" | json_pretty

echo
echo "[5] 정책 매칭"
"${CURL_BIN}" -sG "${BASE_URL}/api/v1/policy/match" \
  --data-urlencode "business_type=카페" \
  --data-urlencode "capital=5000" \
  | json_pretty

echo
echo "[6] AI 채팅 simple"
"${CURL_BIN}" -s -X POST "${BASE_URL}/api/v1/chat/simple" \
  -H "Content-Type: application/json" \
  -d '{"message":"종로3가 카페 창업 어때?","session_id":"smoke-test","user_context":{}}' \
  | json_pretty

echo
echo "=== 테스트 완료 ==="
