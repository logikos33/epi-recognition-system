#!/usr/bin/env python3
"""Inicialização simples do EPI Monitor no Railway."""
import os

PORT = os.environ.get('PORT', '8080')

# Iniciar diretamente o gunicorn sem migrations automáticas
# (Migrations devem ser rodadas manualmente se necessário)
os.execvp('gunicorn', [
    'gunicorn', 
    '--worker-class', 'sync',
    '-w', '1', 
    '--bind', f'0.0.0.0:{PORT}',
    '--timeout', '120', 
    '--log-level', 'info',
    '--access-logfile', '-', 
    '--error-logfile', '-',
    'api_server:app'
])
