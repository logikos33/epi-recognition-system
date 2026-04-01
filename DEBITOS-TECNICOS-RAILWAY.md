# DÉBITOS TÉCNICOS - PRODUÇÃO RAILWAY
**Data:** 1 Abr 2026
**Branch:** V2-clean (staging)
**Status:** Pronto para deploy com ajustes

---

## 🚨 CRÍTICOS (Bloqueiam produção)

### 1. ❌ Migration 001 Ausente
**Problema:** Não existe arquivo `migrations/001_*.sql` com schema inicial (tabelas users, products, etc.)

**Impacto:** Banco não é criado do zero em produção fresca.

**Arquivos Existentes:**
- ✅ `railway-schema-simple.sql` (schema completo na raiz)
- ✅ `migrations/002_create_cameras_table.sql`
- ✅ `migrations/003-008_*.sql` (todas as migrations)

**Solução:**
```bash
# Criar migration 001
cp railway-schema-simple.sql migrations/001_create_base_tables.sql
git add migrations/001_create_base_tables.sql
git commit -m "fix: add migration 001 with base schema"
git push origin V2-clean
```

**Tempo:** 5 minutos

---

### 2. ⚠️ CORS Permissivo em Produção
**Problema:** `CORS_ORIGINS=*` permite requests de qualquer origem.

**Código:** `api_server.py:69`
```python
CORS(app, origins=os.environ.get('CORS_ORIGINS', '*').split(','))
```

**Impacto:** Segurança - qualquer site pode fazer requests para sua API.

**Solução:**
```bash
# Railway dashboard → Variables
CORS_ORIGINS=https://seu-dominio.com,https://app.seu-dominio.com
```

**Tempo:** 2 minutos

---

### 3. 🔐 Secrets em Documentação (Risco Moderado)
**Problema:** Arquivos de documentação contêm secrets reais.

**Arquivos Afetados:**
- `QUICKSTART-Railway.md:23-25` - JWT_SECRET_KEY, SECRET_KEY, CAMERA_SECRET_KEY
- `BROWSER-DEPLOY-GUIDE.md` - secrets nos exemplos

**Impacto:** Documentação pública pode expor secrets de desenvolvimento.

**Solução:**
```bash
# Substituir secrets por placeholders
sed -i '' 's/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=<gerar-32-hex>/' QUICKSTART-Railway.md
sed -i '' 's/SECRET_KEY=.*/SECRET_KEY=<gerar-32-hex>/' QUICKSTART-Railway.md
sed -i '' 's/CAMERA_SECRET_KEY=.*/CAMERA_SECRET_KEY=<gerar-32-hex>/' QUICKSTART-Railway.md

# Commit
git add QUICKSTART-Railway.md BROWSER-DEPLOY-GUIDE.md
git commit -m "security: replace hardcoded secrets with placeholders"
git push origin V2-clean
```

**Tempo:** 3 minutos

---

## ⚠️ ALTOS (Funcionalidade comprometida)

### 4. 📦 Frontend Build Desatualizado
**Problema:** `frontend-new/dist/` existe mas pode estar desatualizado.

**Verificar:**
```bash
# Ver data do build
ls -la frontend-new/dist/index.html

# Rebuild se necessário
cd frontend-new
npm run build
cd ..
git add frontend-new/dist/
git commit -m "chore: rebuild frontend for production"
git push origin V2-clean
```

**Impacto:** Frontend pode não ter últimas mudanças.

**Tempo:** 2 minutos

---

### 5. 🔄 Worker Não Implementado no Deploy
**Problema:** Microserviços Worker foi criado mas não é deployado.

**Arquivos Criados:**
- ✅ `services/shared/events.py` - Redis pub/sub
- ✅ `services/worker/worker_server.py` - Worker FFmpeg+YOLO
- ✅ `services/api_worker_proxy.py` - API → Worker proxy
- ✅ `railway_start.py` - Detecta SERVICE_TYPE

**Falta:**
- ❌ Worker service no Railway
- ❌ Redis service no Railway

**Solução:** Seguir `BROWSER-DEPLOY-GUIDE.md` passo 10 (opcional)

**Impacto:** Sem Worker = processamento de câmeras não escalará.

**Prioridade:** BAIXA - só adicionar quando tiver câmeras reais.

---

### 6. 🗄️ Migrations em Ordem Alfabética
**Problema:** `railway_start.py` roda migrations em ordem alfabética, mas pode haver dependências.

**Código:** `railway_start.py:95`
```python
for f in sorted(glob.glob('migrations/*.sql')):
```

**Verificar:**
```bash
ls -la migrations/*.sql | awk '{print $9}'
```

**Resultado Atual:**
```
migrations/002_create_cameras_table.sql
migrations/003_create_yolo_training_tables.sql
migrations/004_alter_training_videos_add_processing_columns.sql
migrations/005_add_name_to_training_videos.sql
migrations/005_create_frame_annotations_table.sql  # CONFLITO! Dois 005
migrations/006_create_training_jobs_tables.sql
migrations/007_camera_management.sql
migrations/008_rules_engine.sql
```

**Problema:** Dois arquivos `005_*.sql`!

**Solução:**
```bash
# Renomear um dos 005
mv migrations/005_add_name_to_training_videos.sql migrations/005b_add_name_to_training_videos.sql
# Ou melhor: usar timestamp
mv migrations/005_add_name_to_training_videos.sql migrations/20260329_005_add_name.sql

git add migrations/
git commit -m "fix: rename conflicting migration 005 files"
git push origin V2-clean
```

**Tempo:** 5 minutos

---

### 7. 🔗 Redis Não Verificado no Startup
**Problema:** `railway_start.py` não verifica se Redis está acessível.

**Código:** `railway_start.py:16-18`
```python
REDIS   = os.environ.get('REDIS_URL', '')
log.info(f"REDIS_URL    : {'OK' if REDIS else 'ausente'}")
```

**Mas NÃO há:**
```python
def check_redis():
    if not REDIS:
        log.warning("REDIS_URL não definida - Worker não funcionará")
        return False
    try:
        import redis
        r = redis.from_url(REDIS)
        r.ping()
        log.info("✅ Redis OK")
        return True
    except Exception as e:
        log.error(f"Redis inacessível: {e}")
        return False
```

**Impacto:** API pode startar mas Worker não funcionará silenciosamente.

**Solução:** Adicionar `check_redis()` em `railway_start.py`

**Prioridade:** BAIXA - só quando Worker for deployado.

---

## 🟡 MÉDIOS (Risco de falha)

### 8. 🏥 Health Check Incompleto
**Problema:** `/health` não verifica conexões críticas.

**Código Atual:** `api_server.py`
```python
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'api',
        'timestamp': time.time()
    })
```

**Deveria verificar:**
- PostgreSQL connection
- Redis connection (se configurado)
- Worker availability (se configurado)

**Solução:**
```python
@app.route('/health', methods=['GET'])
def health_check():
    checks = {
        'status': 'healthy',
        'service': 'api',
        'timestamp': time.time(),
        'checks': {
            'database': check_db_health(),
            'redis': check_redis_health() if os.environ.get('REDIS_URL') else 'not_configured'
        }
    }
    all_healthy = all(v in ['ok', 'not_configured'] for v in checks['checks'].values())
    checks['status'] = 'healthy' if all_healthy else 'degraded'
    return jsonify(checks), 200 if all_healthy else 503
```

**Tempo:** 15 minutos

---

### 9. 📝 Logs Estruturados Ausentes
**Problema:** Logs são texto puro, difícil de debugar em produção.

**Exemplo Atual:**
```python
log.info("✅ Banco OK")
```

**Deveria ser:**
```python
import structlog

logger = structlog.get_logger()
logger.info("database.connected", database_url=DB_URL.split('@')[1] if '@' in DB_URL else 'unknown')
```

**Impacto:** Difícil troubleshooting em Railway logs.

**Solução:** Adicionar `structlog` ao `requirements.txt` e configurar.

**Prioridade:** BAIXA - melhoria de qualidade.

---

### 10. 🎯 YOLO Model Path Não Validado
**Problema:** `YOLO_MODEL_PATH` assume que arquivo existe.

**Código:** `services/worker/worker_server.py:32`
```python
YOLO_MODEL = os.environ.get('YOLO_MODEL_PATH', 'storage/models/active/model.pt')
```

**Problema:** Se arquivo não existir, Worker crashará em runtime.

**Solução:**
```python
import os
from pathlib import Path

YOLO_MODEL = os.environ.get('YOLO_MODEL_PATH', 'storage/models/active/model.pt')
if not Path(YOLO_MODEL).exists():
    logger.warning(f"YOLO model not found at {YOLO_MODEL}, using default")
    YOLO_MODEL = 'models/yolov8n.pt'  # Backup default
```

**Tempo:** 5 minutos

---

## 🔵 BAIXOS (Qualidade)

### 11. 📚 README.md Incompleto
**Problema:** README.md não tem seção de deploy Railway.

**Solução:** Adicionar seção com link para `BROWSER-DEPLOY-GUIDE.md`.

---

### 12. 🧪 Testes de Integração Ausentes
**Problema:** Não há testes E2E para validar deploy completo.

**Solução:** Criar `tests/test_railway_deploy.py` com testes críticos.

---

### 13. 🔄 Variáveis de Ambiente Não Documentadas
**Problema:** `railway-secrets.txt` existe mas não é `.env.example`.

**Solução:**
```bash
mv railway-secrets.txt .env.example
# Substituir secrets por placeholders
sed -i '' 's/=.*/=<valor>/' .env.example

git add .env.example
git commit -m "docs: add .env.example with all required vars"
git push origin V2-clean
```

---

## 📋 CHECKLIST DEPLOY PRODUÇÃO

### Antes do Deploy (Obrigatório)

- [ ] **Criar migration 001** (5 min)
  ```bash
  cp railway-schema-simple.sql migrations/001_create_base_tables.sql
  git commit -m "fix: add migration 001 with base schema"
  ```

- [ ] **Renomear migrations conflitantes** (5 min)
  ```bash
  # Ver se há conflito
  ls migrations/005*.sql
  # Renomear se necessário
  ```

- [ ] **Configurar CORS_ORIGINS** (2 min)
  ```bash
  # Railway dashboard
  CORS_ORIGINS=https://dominio-producao.com
  ```

- [ ] **Remover secrets da documentação** (3 min)
  ```bash
  sed -i '' 's/<secret>/<placeholder>/g' QUICKSTART-Railway.md
  ```

- [ ] **Rebuild frontend** (2 min)
  ```bash
  cd frontend-new && npm run build && cd ..
  git add frontend-new/dist/
  ```

### Durante Deploy (Monitorar)

- [ ] Verificar logs: `✅ PostgreSQL conectado`
- [ ] Verificar logs: `✅ Migrations executadas`
- [ ] Verificar logs: `✅ Admin criado`
- [ ] Verificar health: `curl /health`

### Após Deploy (Validar)

- [ ] Login funciona: `POST /api/auth/login`
- [ ] Dashboard carrega: `GET /api/dashboard/kpis`
- [ ] Câmeras listam: `GET /api/cameras` (mesmo vazio)
- [ ] Sem erros 500 nos logs

---

## 🎯 ORDEM DE CORREÇÃO RECOMENDADA

### 1. Antes de Deploy (15 minutos totais)
1. Migration 001 (5 min) - CRÍTICO
2. Renomear migrations 005 (5 min) - CRÍTICO
3. Rebuild frontend (2 min) - ALTO
4. Remover secrets docs (3 min) - MÉDIO

### 2. No Railway Dashboard (2 minutos)
1. Configurar CORS_ORIGINS

### 3. Pós-Deploy (Opcional, melhorias)
1. Health check melhorado (15 min)
2. YOLO model validação (5 min)
3. Adicionar .env.example (5 min)

---

## 📊 STATUS FINAL

**Débitos Críticos:** 3 (todos < 5 min para corrigir)
**Débitos Altos:** 4
**Débitos Médios:** 3
**Débitos Baixos:** 3

**Tempo Total para Produção:** ~20 minutos

**Veredito:** ✅ **PRONTO PARA DEPLOY** após correções críticas

---

## 🔗 REFERÊNCIAS

- Guia Deploy: `BROWSER-DEPLOY-GUIDE.md`
- Quickstart: `RAILWAY-QUICKSTART.txt`
- Schema: `railway-schema-simple.sql`
- Migrations: `migrations/`

---

*Gerado: 2026-04-01*
*Autor: Claude Sonnet 4.5*
*Revisão: Débitos técnicos para produção Railway*
