#!/bin/bash
# ==============================================================================
# CORRIGIR DÉBITOS CRÍTICOS - PRODUÇÃO RAILWAY
# Data: 1 Abr 2026
# Tempo estimado: 20 minutos
# ==============================================================================

set -e  # Parar em qualquer erro

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║           CORRIGINDO DÉBITOS CRÍTICOS - RAILWAY PRODUÇÃO                  ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# ==============================================================================
# 1. MIGRATION 001 AUSENTE (5 min)
# ==============================================================================
echo "┌─ [1/5] CRIANDO MIGRATION 001 ─────────────────────────────────────────────┐"
echo ""

if [ -f "migrations/001_*.sql" ]; then
    echo "✅ Migration 001 já existe"
else
    echo "Criando migration 001..."
    cp railway-schema-simple.sql migrations/001_create_base_tables.sql
    echo "✅ Migration 001 criada: migrations/001_create_base_tables.sql"
fi

echo ""
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

# ==============================================================================
# 2. RENOMEAR MIGRATIONS 005 (5 min)
# ==============================================================================
echo "┌─ [2/5] RENOMEANDO MIGRATIONS 005 ───────────────────────────────────────────┐"
echo ""

if [ -f "migrations/005_add_name_to_training_videos.sql" ] && [ -f "migrations/005_create_frame_annotations_table.sql" ]; then
    echo "Conflito detectado: dois arquivos 005"
    echo "Renomeando 005_add_name → 005b_add_name..."

    mv migrations/005_add_name_to_training_videos.sql migrations/005b_add_name_to_training_videos.sql
    echo "✅ Renomeado para: migrations/005b_add_name_to_training_videos.sql"
else
    echo "✅ Sem conflito de migrations 005"
fi

echo ""
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

# ==============================================================================
# 3. REBUILD FRONTEND (2 min)
# ==============================================================================
echo "┌─ [3/5] REBUILD FRONTEND ────────────────────────────────────────────────────┐"
echo ""

echo "Entrando em frontend-new..."
cd frontend-new

echo "Instalando dependências (se necessário)..."
npm install --silent

echo "Buildando frontend..."
npm run build

echo "✅ Frontend buildado em frontend-new/dist/"

cd ..
echo ""
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

# ==============================================================================
# 4. REMOVER SECRETS DA DOCUMENTAÇÃO (3 min)
# ==============================================================================
echo "┌─ [4/5] REMOVENDO SECRETS DA DOCUMENTAÇÃO ───────────────────────────────────┐"
echo ""

echo "Substituindo secrets em QUICKSTART-Railway.md..."
sed -i.bak 's/JWT_SECRET_KEY=c95c9deea5d12c6c29c5cb0904f31d33fd5796aa550bcdd096d2b70f43229b8b/JWT_SECRET_KEY=<gerar-32-hex>/' QUICKSTART-Railway.md
sed -i.bak 's/SECRET_KEY=cc0f18f0c496acbf695dbde98bfce0349cdd1af3cd8a616923b84f37afd6c03a/SECRET_KEY=<gerar-32-hex>/' QUICKSTART-Railway.md
sed -i.bak 's/CAMERA_SECRET_KEY=LgcYZ-oaTO5dla6qEobzO_DMPcc-MGE4Uxzue3xYbc0/CAMERA_SECRET_KEY=<gerar-32-hex>/' QUICKSTART-Railway.md

echo "Substituindo secrets em BROWSER-DEPLOY-GUIDE.md..."
sed -i.bak 's/JWT_SECRET_KEY=c95c9deea5d12c6c29c5cb0904f31d33fd5796aa550bcdd096d2b70f43229b8b/JWT_SECRET_KEY=<gerar-32-hex>/' BROWSER-DEPLOY-GUIDE.md
sed -i.bak 's/SECRET_KEY=cc0f18f0c496acbf695dbde98bfce0349cdd1af3cd8a616923b84f37afd6c03a/SECRET_KEY=<gerar-32-hex>/' BROWSER-DEPLOY-GUIDE.md
sed -i.bak 's/CAMERA_SECRET_KEY=LgcYZ-oaTO5dla6qEobzO_DMPcc-MGE4Uxzue3xYbc0/CAMERA_SECRET_KEY=<gerar-32-hex>/' BROWSER-DEPLOY-GUIDE.md

echo "✅ Secrets substituídos por placeholders"
echo "📝 Backups criados com extensão .bak"

echo ""
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

# ==============================================================================
# 5. CRIAR .ENV.EXAMPLE
# ==============================================================================
echo "┌─ [5/5] CRIANDO .ENV.EXAMPLE ─────────────────────────────────────────────────┐"
echo ""

if [ ! -f ".env.example" ]; then
    echo "Criando .env.example..."
    cat > .env.example << 'EOF'
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Redis (opcional - Worker)
REDIS_URL=redis://host:port

# JWT Secrets - GERAR NOVOS PARA PRODUÇÃO!
JWT_SECRET_KEY=<gerar-openssl-rand-hex-32>
SECRET_KEY=<gerar-openssl-rand-hex-32>
CAMERA_SECRET_KEY=<gerar-openssl-rand-hex-32>

# API Config
FLASK_ENV=production
PORT=8080
CORS_ORIGINS=https://seu-dominio.com

# Admin User (criado automaticamente no primeiro deploy)
ADMIN_EMAIL=admin@empresa.com
ADMIN_PASSWORD=<senha-forte-aqui>
ADMIN_NAME=Administrador

# YOLO Config (opcional)
YOLO_MODEL_PATH=storage/models/active/model.pt
DETECTION_CONFIDENCE_THRESHOLD=0.5

# FFmpeg Config (opcional)
FFMPEG_LOG_LEVEL=warning
FFMPEG_PRESET=ultrafast
FFMPEG_VIDEO_BITRATE=512k
FFMPEG_RESOLUTION=640x360

# HLS Config (opcional)
HLS_SEGMENT_DURATION=1
HLS_PLAYLIST_SIZE=3

# Health Monitoring (opcional)
STREAM_HEALTH_CHECK_INTERVAL=30
MAX_STREAM_RESTARTS=3
EOF
    echo "✅ .env.example criado"
else
    echo "✅ .env.example já existe"
fi

echo ""
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

# ==============================================================================
# COMMITAR TUDO
# ==============================================================================
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  COMMITAR MUDANÇAS                                                         ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

echo "Adicionando arquivos ao git..."
git add migrations/001_create_base_tables.sql
git add migrations/005b_add_name_to_training_videos.sql
git add frontend-new/dist/
git add QUICKSTART-Railway.md BROWSER-DEPLOY-GUIDE.md
git add .env.example

echo ""
echo "Status do git:"
git status --short

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  PRÓXIMO PASSO                                                              ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Execute para commitar:"
echo ""
echo "  git commit -m \"fix: corrigir débitos críticos para produção Railway"
echo ""
echo "- Adiciona migration 001 (schema base)"
echo "- Renomeia migration 005 conflitante"
echo "- Rebuild frontend produção"
echo "- Remove secrets da documentação"
echo "- Adiciona .env.example\""
echo ""
echo "  git push origin V2-clean"
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  APÓS PUSH - CONFIGURAR RAILWAY DASHBOARD                                 ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "1. Acessar: https://railway.app/project/366c8fae-197b-4e55-9ec9-b5261b3f4b62"
echo "2. Selecionar ambiente: Pré-Produção"
echo "3. Criar serviços: API (GitHub), PostgreSQL, Redis"
echo "4. Configurar variáveis (ver RAILWAY-QUICKSTART.txt)"
echo "5. ESPECIALMENTE IMPORTANTE:"
echo "   CORS_ORIGINS=https://seu-dominio-production.com"
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  ✅ DÉBITOS CRÍTICOS CORRIGIDOS!                                          ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
