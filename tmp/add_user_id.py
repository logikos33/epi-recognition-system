import os
import sys
sys.path.insert(0, os.getcwd())

from backend.database import get_db_context
from sqlalchemy import text

print("=== PASSO 1: ADICIONAR user_id À training_videos ===")

with get_db_context() as db:
    # Adicionar coluna user_id
    try:
        db.execute(text("""
            ALTER TABLE training_videos
            ADD COLUMN IF NOT EXISTS user_id UUID
            REFERENCES users(id) ON DELETE SET NULL
        """))
        db.commit()
        print("✅ Coluna user_id adicionada")
    except Exception as e:
        print(f"⚠️  user_id já existe ou erro: {e}")

    # Buscar ID do admin
    print("\n=== PASSO 2: BUSCAR ADMIN ===")
    result = db.execute(text("SELECT id, email FROM users WHERE email LIKE '%admin%' LIMIT 5"))
    admins = result.fetchall()

    if not admins:
        print("❌ Nenhum admin encontrado - criando admin padrão")
        # Criar admin
        from bcrypt import hashpw, gensalt
        password = 'Admin@2024'
        hashed = hashpw(password.encode(), gensalt()).decode()

        db.execute(text("""
            INSERT INTO users (email, password_hash, full_name)
            VALUES (%s, %s, %s)
            RETURNING id, email
        """), ('admin@epimonitor.com', hashed, 'Administrador'))
        db.commit()

        result = db.execute(text("SELECT id, email FROM users WHERE email = 'admin@epimonitor.com'"))
        admins = result.fetchall()
        print(f"✅ Admin criado: {admins[0]}")
    else:
        print(f"✅ Admin encontrado: {admins[0]}")

    admin_id = admins[0][0]
    print(f"Admin ID: {admin_id}")

    # Atribuir videos ao admin
    print("\n=== PASSO 3: ATRIBUIR VIDEOS ÓRFÃOS AO ADMIN ===")
    result = db.execute(text("""
        UPDATE training_videos
        SET user_id = :admin_id
        WHERE user_id IS NULL
        RETURNING id, filename
    """), {'admin_id': admin_id})

    updated = result.fetchall()
    db.commit()

    print(f"✅ {len(updated)} videos atribuídos ao admin:")
    for v in updated[:3]:
        print(f"   → {str(v[0])[:8]} {v[1][:50]}")

print("\n=== VERIFICAÇÃO FINAL ===")
with get_db_context() as db:
    result = db.execute(text("""
        SELECT id, filename, user_id, project_id
        FROM training_videos
        LIMIT 5
    """))

    print("Videos após correção:")
    for r in result.fetchall():
        user = str(r[2])[:8] if r[2] else "NULL"
        project = str(r[3])[:8] if r[3] else "NULL"
        print(f"  {str(r[0])[:8]} {r[1][:40]} user={user} project={project}")
