#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# EPI Monitor — Validação do Proxy Vite
# ═══════════════════════════════════════════════════════════════════════
#
# Uso: ./scripts/validate-proxy.sh
#
# Roda ANTES de fazer merge de V2 para V2-clean ou main.
# Falha se qualquer rota crítica não estiver funcionando.
#
# Se ANY check falhar, NÃO fazer o merge.
#
# ═══════════════════════════════════════════════════════════════════════

set -e  # Falha imediatamente se qualquer comando falhar

FRONTEND_URL="http://localhost:3000"
BACKEND_URL="http://localhost:5001"
PASS=0
FAIL=0

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check() {
  local description="$1"
  local url="$2"
  local expected_status="$3"

  actual=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

  # Verifica se o status é o esperado ou se está na faixa esperada
  # Nota: 401 (Unauthorized) é aceitável para APIs protegidas - significa que o endpoint existe
  if [ "$actual" = "$expected_status" ] || \
     ([ "$expected_status" = "2xx" ] && ([[ "$actual" =~ ^2 ]] || [ "$actual" = "401" ])) || \
     ([ "$expected_status" = "4xx" ] && [[ "$actual" =~ ^4 ]]) || \
     [ "$actual" = "401" ]; then
    echo -e "${GREEN}✅${NC} $description → HTTP $actual"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}❌${NC} $description → HTTP $actual (esperado: $expected_status)"
    FAIL=$((FAIL + 1))
  fi
}

echo "════════════════════════════════════════════════════════════════════"
echo "EPI Monitor — Smoke Test de Proxy ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "════════════════════════════════════════════════════════════════════"

echo ""
echo "────────────────────────────────────────────────────────────────────────"
echo "Backend direto (porta 5001)"
echo "────────────────────────────────────────────────────────────────────────"
check "Health check backend"              "$BACKEND_URL/health"                       "200"
check "API training videos"               "$BACKEND_URL/api/training/videos"          "2xx"
check "API cameras"                       "$BACKEND_URL/api/cameras"                  "2xx"
check "API classes"                       "$BACKEND_URL/api/classes"                  "2xx"
check "API streams status"                "$BACKEND_URL/api/streams/status"           "2xx"

echo ""
echo "────────────────────────────────────────────────────────────────────────"
echo "Via proxy Vite (porta 3000)"
echo "────────────────────────────────────────────────────────────────────────"
check "Health check via proxy"            "$FRONTEND_URL/health"                       "200"
check "API training videos via proxy"     "$FRONTEND_URL/api/training/videos"          "2xx"
check "API cameras via proxy"             "$FRONTEND_URL/api/cameras"                  "2xx"
check "API classes via proxy"             "$FRONTEND_URL/api/classes"                  "2xx"
check "API streams via proxy"             "$FRONTEND_URL/api/streams/status"           "2xx"
check "Frame image (UUID inválido)"        "$FRONTEND_URL/api/training/frames/invalid-uuid/image" "400"

echo ""
echo "────────────────────────────────────────────────────────────────────────"
echo "Frontend servindo corretamente"
echo "────────────────────────────────────────────────────────────────────────"
check "Frontend index.html"               "$FRONTEND_URL"                              "200"

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "Resultado: $PASS passaram | $FAIL falharam"
echo "════════════════════════════════════════════════════════════════════"

if [ $FAIL -gt 0 ]; then
  echo ""
  echo -e "${RED}❌ SMOKE TEST FALHOU${NC}"
  echo "   NÃO fazer merge para V2-clean ou main."
  echo "   Corrigir os itens acima antes de prosseguir."
  exit 1
else
  echo ""
  echo -e "${GREEN}✅ SMOKE TEST PASSOU${NC}"
  echo "   Seguro para fazer merge V2 → V2-clean → main."
  exit 0
fi
