#!/usr/bin/env python3
"""
EPI Monitor — Inicialização Railway.
SERVICE_TYPE=api    → Flask API (padrão)
SERVICE_TYPE=worker → Worker FFmpeg/YOLO
"""
import os, sys, glob, logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [INIT] %(levelname)s %(message)s'
)
log = logging.getLogger(__name__)

# ── Variáveis ────────────────────────────────────────────────
SERVICE = os.environ.get('SERVICE_TYPE', 'api')
PORT    = os.environ.get('PORT', '8080')
DB_URL  = os.environ.get('DATABASE_URL', '')
REDIS   = os.environ.get('REDIS_URL', '')

# Corrigir prefixo Railway
if DB_URL.startswith('postgres://'):
    DB_URL = DB_URL.replace('postgres://', 'postgresql://', 1)
    os.environ['DATABASE_URL'] = DB_URL

log.info(f"SERVICE_TYPE : {SERVICE}")
log.info(f"PORT         : {PORT}")
log.info(f"DATABASE_URL : {'OK' if DB_URL else 'AUSENTE'}")
log.info(f"REDIS_URL    : {'OK' if REDIS else 'ausente'}")

# ── Verificar banco ──────────────────────────────────────────
def check_db():
    if not DB_URL:
        log.error("DATABASE_URL não definida")
        return False
    try:
        import psycopg2
        c = psycopg2.connect(DB_URL, connect_timeout=15)
        c.cursor().execute("SELECT 1")
        c.close()
        log.info("✅ Banco OK")
        return True
    except Exception as e:
        log.error(f"Banco inacessível: {e}")
        return False

# ── Migrations ───────────────────────────────────────────────
def run_migrations():
    log.info("=== Migrations ===")
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        for f in sorted(glob.glob('migrations/*.sql')):
            log.info(f"  {f}...")
            try:
                cur.execute(open(f).read())
                conn.commit()
                log.info(f"  ✅")
            except Exception as e:
                conn.rollback()
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    log.info(f"  já existe (OK)")
                else:
                    log.error(f"  ❌ {e}")
        conn.close()
        log.info("✅ Migrations OK")
        return True
    except Exception as e:
        log.error(f"Migrations: {e}")
        return False

# ── Criar admin ──────────────────────────────────────────────
def create_admin():
    try:
        import psycopg2, bcrypt
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT EXISTS(
                SELECT FROM information_schema.tables
                WHERE table_schema='public' AND table_name='users'
            )
        """)
        if not cur.fetchone()[0]:
            log.info("Tabela users não existe — pulando admin")
            conn.close()
            return
        email    = os.environ.get('ADMIN_EMAIL',    'admin@epimonitor.com')
        password = os.environ.get('ADMIN_PASSWORD', 'EpiMonitor@2024!')
        name     = os.environ.get('ADMIN_NAME',     'Administrador')
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            log.info(f"  Admin já existe: {email}")
        else:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            try:
                cur.execute(
                    "INSERT INTO users (email,password_hash,name,role) VALUES(%s,%s,%s,'admin')",
                    (email, hashed, name)
                )
            except Exception:
                cur.execute(
                    "INSERT INTO users (email,password_hash,name) VALUES(%s,%s,%s)",
                    (email, hashed, name)
                )
            conn.commit()
            log.info(f"  ✅ Admin criado: {email} / {password}")
        conn.close()
    except Exception as e:
        log.warning(f"Admin: {e}")

# ── Iniciar API ──────────────────────────────────────────────
def start_api():
    log.info(f"=== Iniciando API na porta {PORT} ===")

    # Detectar módulo correto
    module = None
    for name in ['api_server', 'app', 'main']:
        if os.path.exists(f'{name}.py'):
            module = name
            break
    if not module:
        log.error("Nenhum arquivo de API encontrado")
        sys.exit(1)
    log.info(f"Módulo: {module}:app")

    # Worker class
    try:
        import eventlet
        worker_class, workers = 'eventlet', '1'
        log.info("Worker: eventlet (WebSocket)")
    except ImportError:
        worker_class, workers = 'sync', '2'
        log.warning("Worker: sync (sem WebSocket)")

    os.execvp('gunicorn', [
        'gunicorn',
        '--worker-class', worker_class,
        '-w', workers,
        '--bind', f'0.0.0.0:{PORT}',
        '--timeout', '120',
        '--keep-alive', '5',
        '--log-level', 'info',
        '--access-logfile', '-',
        '--error-logfile', '-',
        f'{module}:app'
    ])

# ── Iniciar Worker ───────────────────────────────────────────
def start_worker():
    log.info("=== Iniciando Worker ===")
    if not REDIS:
        log.error("REDIS_URL obrigatório para Worker")
        sys.exit(1)
    try:
        import redis as r
        r.from_url(REDIS).ping()
        log.info("✅ Redis OK")
    except Exception as e:
        log.error(f"Redis: {e}")
        sys.exit(1)

    sys.path.insert(0, '.')
    from services.worker.worker_server import main
    main()

# ── Main ─────────────────────────────────────────────────────
if SERVICE == 'api':
    if not check_db():
        sys.exit(1)
    run_migrations()
    create_admin()
    start_api()

elif SERVICE == 'worker':
    check_db()
    start_worker()

else:
    log.error(f"SERVICE_TYPE inválido: '{SERVICE}' — use 'api' ou 'worker'")
    sys.exit(1)
