#!/usr/bin/env python3
"""Inicialização do EPI Monitor no Railway: migrations + admin + servidor."""
import os, sys, glob, subprocess

DATABASE_URL = os.environ.get('DATABASE_URL')
PORT = os.environ.get('PORT', '8080')

def run_migrations():
    print("=== Migrations ===")
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        for f in sorted(glob.glob('migrations/*.sql')):
            print(f"  {f}...")
            try:
                with open(f) as mf:
                    sql = mf.read()
                    if sql.strip():
                        cur.execute(sql)
                conn.commit()
                print(f"  ✅ {f}")
            except Exception as e:
                conn.rollback()
                print(f"  ⚠️  {f}: {e}")
        conn.close()
        print("✅ Migrations concluídas")
    except Exception as e:
        print(f"❌ Migrations: {e}")
        sys.exit(1)

def create_admin():
    print("=== Admin ===")
    try:
        import psycopg2, bcrypt
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        email = os.environ.get('ADMIN_EMAIL', 'admin@epimonitor.com')
        password = os.environ.get('ADMIN_PASSWORD', 'EpiMonitor@2024!')
        name = os.environ.get('ADMIN_NAME', 'Administrador')
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            print(f"  ✅ Admin já existe: {email}")
        else:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO users (email, password_hash, full_name, role) VALUES (%s,%s,%s,'admin')",
                (email, hashed, name)
            )
            conn.commit()
            print(f"  ✅ Admin criado: {email}")
        conn.close()
    except Exception as e:
        print(f"  ⚠️  Admin: {e}")

def start_server():
    print(f"=== Servidor porta {PORT} ===")
    os.execvp('gunicorn', [
        'gunicorn', '--worker-class', 'eventlet',
        '-w', '1', '--bind', f'0.0.0.0:{PORT}',
        '--timeout', '120', '--log-level', 'info',
        '--access-logfile', '-', '--error-logfile', '-',
        'api_server:app'
    ])

if not DATABASE_URL:
    print("❌ DATABASE_URL não definida")
    sys.exit(1)

run_migrations()
create_admin()
start_server()
