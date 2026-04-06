#!/bin/sh
# Railway startup script — ensures $PORT is expanded by shell
set -e
echo "[START] PORT=$PORT"
echo "[START] Starting gunicorn..."
exec gunicorn minimal_wsgi:app \
    --workers 1 \
    --timeout 60 \
    --bind "0.0.0.0:${PORT:-8080}" \
    --log-level info \
    --access-logfile -
