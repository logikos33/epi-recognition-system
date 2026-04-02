#!/bin/bash

echo "Verificando logs do Railway..."
echo ""

# Link ao projeto
railway link \
  --project 366c8fae-197b-4e55-9ec9-b5261b3f4b62 \
  --environment d1b84aae-b1e6-459e-a02d-3f1e83737b52 \
  --service 0fa9ab7e-0a5e-4448-a177-700e4d76a9ec >/dev/null 2>&1

echo "Últimas linhas dos logs de deploy:"
railway logs | grep -i "error\|fail\|npm\|node\|vite\|build" | tail -50
