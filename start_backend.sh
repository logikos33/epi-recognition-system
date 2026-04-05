#!/bin/bash
# EPI Monitor — Backend com self-healing automático
# USO: ./start_backend.sh
# Reinicia automaticamente se cair (até 10 tentativas com backoff exponencial)

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_RESTARTS=10
RESTART_COUNT=0
RESTART_DELAY=3

cd "$PROJECT_DIR"
source venv/bin/activate 2>/dev/null || true
export $(cat .env | grep -v '^#' | xargs) 2>/dev/null || true
mkdir -p logs

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [EPI-BACKEND] $1" | tee -a logs/api_server.log
}

log "=== EPI Monitor Backend iniciando ==="

# Verificar dependências críticas
python3 -c "import flask, psycopg2" 2>/dev/null || {
    log "ERRO CRÍTICO: Dependências faltando. Rodar: pip install -r requirements.txt"
    exit 1
}

# Verificar variável obrigatória
[ -z "$DATABASE_URL" ] && {
    log "ERRO CRÍTICO: DATABASE_URL não definida no .env"
    exit 1
}

while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    log "Iniciando servidor (tentativa $((RESTART_COUNT + 1))/$MAX_RESTARTS)..."

    python api_server.py 2>&1 | tee -a logs/api_server.log
    EXIT_CODE=${PIPESTATUS[0]}

    # Exit 0 = encerramento normal | 130 = Ctrl+C | 143 = SIGTERM
    [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 130 ] || [ $EXIT_CODE -eq 143 ] && {
        log "Servidor encerrado normalmente (exit $EXIT_CODE)."
        exit 0
    }

    RESTART_COUNT=$((RESTART_COUNT + 1))
    [ $RESTART_COUNT -ge $MAX_RESTARTS ] && break

    log "AVISO: Servidor caiu (exit $EXIT_CODE). Reiniciando em ${RESTART_DELAY}s..."
    log "Último erro:"
    tail -5 logs/api_server.log | grep -i "error\|exception\|traceback" | head -3

    sleep $RESTART_DELAY
    RESTART_DELAY=$(( RESTART_DELAY < 60 ? RESTART_DELAY * 2 : 60 ))
done

log "CRÍTICO: Servidor não iniciou após $MAX_RESTARTS tentativas."
log "Verificar logs/api_server.log para diagnóstico."
exit 1
