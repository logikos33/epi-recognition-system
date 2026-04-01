#!/usr/bin/env python3
"""Inicialização simples do EPI Monitor no Railway."""
import os
import sys

# Verificar se api_server.py pode ser importado
try:
    import api_server
    print("✅ api_server importado com sucesso")
    print(f"✅ app object: {api_server.app}")
except Exception as e:
    print(f"❌ Erro ao importar api_server: {e}")
    sys.exit(1)

PORT = os.environ.get('PORT', '8080')
print(f"🚀 Iniciando gunicorn na porta {PORT}...")

# Iniciar o gunicorn
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
