#!/usr/bin/env python3
"""
Inicialização do EPI Monitor no Railway.
Corrige DATABASE_URL, executa migrations, cria admin, inicia servidor.
"""
import os
import sys
import glob

# ============================================================
# VARIÁVEIS OBRIGATÓRIAS
# ============================================================
DATABASE_URL = os.environ.get('DATABASE_URL', '')
PORT = os.environ.get('PORT', '8080')

# Railway usa postgres:// mas psycopg2 precisa postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    os.environ['DATABASE_URL'] = DATABASE_URL
    print(f"✅ DATABASE_URL prefixo corrigido: postgresql://...")

if not DATABASE_URL:
    print("❌ DATABASE_URL não definida — verificar variáveis no Railway")
    sys.exit(1)

print(f"✅ PORT: {PORT}")
print(f"✅ DATABASE_URL: postgresql://...{DATABASE_URL[-20:]}")

# ============================================================
# MIGRATIONS
# ============================================================
def run_migrations():
    print("\n=== Executando migrations ===")
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        migration_files = sorted(glob.glob('migrations/*.sql'))
        if not migration_files:
            print("  ⚠️  Nenhum arquivo SQL em migrations/")
            conn.close()
            return True
        
        for filepath in migration_files:
            print(f"  Executando {filepath}...")
            try:
                with open(filepath) as f:
                    sql = f.read().strip()
                if sql:
                    cur.execute(sql)
                    conn.commit()
                    print(f"  ✅ {filepath}")
            except Exception as e:
                conn.rollback()
                # Ignorar erros de "já existe" — são esperados em redeploys
                err_str = str(e).lower()
                if 'already exists' in err_str or 'duplicate' in err_str:
                    print(f"  ⚠️  {filepath}: já existe (OK)")
                else:
                    print(f"  ❌ {filepath}: {e}")
        
        conn.close()
        print("✅ Migrations concluídas")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Erro de conexão com banco: {e}")
        print("   Verificar DATABASE_URL no Railway")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado nas migrations: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================
# CRIAR ADMIN
# ============================================================
def create_admin():
    print("\n=== Configurando admin ===")
    try:
        import psycopg2
        import bcrypt
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Verificar se tabela users existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            )
        """)
        if not cur.fetchone()[0]:
            print("  ⚠️  Tabela users não existe ainda — pulando")
            conn.close()
            return
        
        email = os.environ.get('ADMIN_EMAIL', 'admin@epimonitor.com')
        password = os.environ.get('ADMIN_PASSWORD', 'EpiMonitor@2024!')
        name = os.environ.get('ADMIN_NAME', 'Administrador')
        
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            print(f"  ✅ Admin já existe: {email}")
        else:
            hashed = bcrypt.hashpw(
                password.encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Tentar com coluna role, sem role se não existir
            try:
                cur.execute("""
                    INSERT INTO users (email, password_hash, full_name, role)
                    VALUES (%s, %s, %s, 'admin')
                """, (email, hashed, name))
            except Exception:
                cur.execute("""
                    INSERT INTO users (email, password_hash, full_name)
                    VALUES (%s, %s, %s)
                """, (email, hashed, name))
            
            conn.commit()
            print(f"  ✅ Admin criado: {email}")
        
        conn.close()
        
    except Exception as e:
        print(f"  ⚠️  Erro ao criar admin (não crítico): {e}")

# ============================================================
# VERIFICAR SAÚDE DO BANCO
# ============================================================
def check_database():
    print("\n=== Verificando banco ===")
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"  Tabelas: {tables}")
        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ Erro ao conectar ao banco: {e}")
        return False

# ============================================================
# INICIAR SERVIDOR
# ============================================================
def start_server():
    print(f"\n=== Iniciando servidor na porta {PORT} ===")
    
    # Verificar se gunicorn está disponível
    try:
        import gunicorn
        print(f"  gunicorn: {gunicorn.__version__}")
    except ImportError:
        print("  ❌ gunicorn não instalado")
        sys.exit(1)
    
    # Verificar se eventlet está disponível
    try:
        import eventlet
        print(f"  eventlet: {eventlet.__version__}")
    except ImportError:
        print("  ⚠️  eventlet não disponível — usando sync worker")
        # Fallback para worker síncrono
        os.execvp('gunicorn', [
            'gunicorn',
            '-w', '2',
            '--bind', f'0.0.0.0:{PORT}',
            '--timeout', '120',
            '--log-level', 'info',
            '--access-logfile', '-',
            '--error-logfile', '-',
            'api_server:app'
        ])
        return
    
    # Usar eventlet worker para WebSocket
    os.execvp('gunicorn', [
        'gunicorn',
        '--worker-class', 'eventlet',
        '-w', '1',
        '--bind', f'0.0.0.0:{PORT}',
        '--timeout', '120',
        '--keep-alive', '5',
        '--log-level', 'info',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'api_server:app'
    ])

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("EPI Monitor — Iniciando no Railway")
    print("=" * 50)
    
    # 1. Verificar banco
    db_ok = check_database()
    if not db_ok:
        print("❌ Banco inacessível — abortando")
        sys.exit(1)
    
    # 2. Migrations
    migrations_ok = run_migrations()
    if not migrations_ok:
        print("❌ Migrations falharam — abortando")
        sys.exit(1)
    
    # 3. Admin
    create_admin()
    
    # 4. Servidor
    start_server()
