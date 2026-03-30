# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🤖 Agentes Personalizados Disponíveis

Este projeto possui 5 agentes especializados para automatizar tarefas comuns:

| Agente | Arquivo | Quando Usar |
|--------|---------|-------------|
| `corretor-de-codigo` | `.claude/agents/corretor-de-codigo.md` | Após escrever ou modificar código - revisa e corrige automaticamente aplicando clean code, boas práticas e segurança |
| `dev-cleanup` | `.claude/agents/dev-cleanup.md` | Quando o ambiente estiver lento ou travando - elimina processos zumbis, caches obsoletos e libera recursos |
| `guardiao-login` | `.claude/agents/guardiao-login.md` | Após alterar auth, providers ou middlewares - protege a performance do login |
| `doc-versionador` | `.claude/agents/doc-versionador.md` | Após finalizar qualquer feature ou correção - documenta e versiona alterações |
| `railway-deploy` | `.claude/agents/railway-deploy.md` | Para preparar e subir para staging no Railway - otimiza e gera arquivos de infraestrutura |

### Invocações de Exemplo

```
"corrija o código de src/services/auth.py"
"revise e aplique clean code em todos os arquivos de backend/"
"limpe o ambiente"
"está travando, limpa aí"
"valide o login antes de commitar"
"garanta que o login não travou"
"documente as alterações de hoje"
"otimize e prepare para staging no Railway"
```

### Regras Automáticas

- **Sempre** que alterar `frontend/src/lib/auth.ts`, `frontend/src/hooks/useAuth.ts` ou qualquer middleware de autenticação, invoque o `guardiao-login` antes de finalizar
- **Ao concluir** qualquer tarefa com sucesso, invoque o `doc-versionador` para registrar as alterações
- **Ao perceber** lentidão no ambiente, invoque o `dev-cleanup` para liberar recursos

---

## Project Overview

**EPI Recognition System** - A product counting and detection system using YOLOv8 computer vision, designed to automatically count and verify products during vehicle loading operations. The system combines real-time object detection with user verification for high accuracy (85%+ target).

### Tech Stack
- **Backend**: Flask (Python 3.11) with PostgreSQL on Railway
- **Frontend**: Next.js (TypeScript) - migrating from Supabase to REST API
- **AI/ML**: YOLOv8 for object detection (planned: custom-trained models per product)
- **Deployment**: Railway with Nixpacks (2-3 min builds, not Docker)
- **Database**: PostgreSQL with simplified schema (6 tables)
- **Authentication**: JWT tokens with bcrypt password hashing

---

## Architecture

### Backend Structure
```
api_server.py                 # Main Flask app - ALL endpoints defined here
backend/
├── database.py               # SQLAlchemy connection pool, get_db() generator
├── auth_db.py                # User auth, sessions, password hashing (bcrypt)
└── products.py               # ProductService class - products CRUD
```

**Key Pattern**: `api_server.py` is a monolithic Flask app with all routes defined inline. Database operations use raw SQL with SQLAlchemy's `text()` for queries, not ORM models.

### Frontend Structure
```
frontend/src/
├── lib/api.ts                # REST API client - replaces Supabase client
├── hooks/
│   ├── useAuth.ts            # Auth hook with JWT token management
│   └── useProducts.ts        # Products CRUD hook
├── types/
│   └── product.ts            # TypeScript interfaces
└── app/dashboard/products/page.tsx    # Products management UI
```

**Key Pattern**: Frontend uses centralized `api.ts` client with auto Authorization header injection. JWT tokens stored in `localStorage`.

### Database Schema (Simplified)

**6 tables** (railway-schema-simple.sql):
1. `users` - id, email, password_hash, full_name, company_name, created_at, is_active
2. `products` - id, user_id, name, sku, category, description, detection_threshold, is_active, created_at
3. `training_images` - id, user_id, product_id, image_url, is_annotated, created_at
4. `counting_sessions` - id, user_id, vehicle_id, status, started_at, total_products
5. `counted_products` - id, session_id, product_id, confidence, detected_at
6. `sessions` - id, user_id, token, expires_at, created_at (JWT sessions)

**Important**: Schema is simplified from original 13 tables. Columns removed: `phone`, `updated_at`, `last_login`, `refresh_token`, `ip_address`, `user_agent`, `image_url`, `volume_cm3`, `weight_g`.

---

## Development Workflow

### Local Development (Primary Workflow)

**Why local?** Railway builds take 2-3 minutes. Local iterations take ~5 seconds.

```bash
# 1. Start API server locally
cd "/Users/vitoremanuel/Documents/Logikos/CATH/Repositorio Reconhecimento de EPI "
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
python api_server.py

# API runs on http://localhost:5001
# Connected to Railway PostgreSQL (DATABASE_URL in .env)
```

**Auto-reload**: Add `debug=True` to `api_server.py` for automatic reload on file changes:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:5001/health

# Register user
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@local.dev","password":"123456","full_name":"Test"}'

# Login and save token
TOKEN=$(curl -s -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@local.dev","password":"123456"}' | jq -r '.token')

# Create product
curl -X POST http://localhost:5001/api/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Produto Test","sku":"TEST-001","category":"Teste"}'

# List products
curl http://localhost:5001/api/products \
  -H "Authorization: Bearer $TOKEN"
```

### Railway Deployment

**When ready to deploy:**
```bash
git add .
git commit -m "feat: Description"
git push origin main
```

Railway automatically builds with **Nixpacks** (2-3 min). `nixpacks.toml` configures the build - do NOT use Dockerfile (renamed to Dockerfile.backup).

**Check production status:**
```bash
curl https://epi-recognition-system-production.up.railway.app/health
```

---

## Key Architectural Decisions

### 1. No ORM Models - Raw SQL with SQLAlchemy
- Uses `sqlalchemy.text()` for raw SQL queries
- Direct tuple/array access from `fetchone()` results
- Example: `row[0]` for first column, not `row.id`
- **Benefit**: Explicit control, matches simplified schema exactly

### 2. Monolithic Flask App
- All 500+ routes in single `api_server.py` file
- Backend modules (`auth_db.py`, `products.py`) are service classes, not Flask blueprints
- **Benefit**: Simple deployment, easy to read endpoint logic

### 3. Frontend Migration: Supabase → REST API
- Previously used Supabase client directly
- Now uses custom `api.ts` REST client with JWT tokens
- **Benefit**: Provider independence, better error handling

### 4. Simplified Database Schema
- Original plan: 13 tables with full audit columns
- Current: 6 essential tables (removed `updated_at`, `last_login`, etc.)
- **Benefit**: Faster development, easier to migrate

### 5. Nixpacks over Docker
- Dockerfile builds: ~10 minutes
- Nixpacks builds: ~2-3 minutes
- `nixpacks.toml` handles Python 3.11, OpenCV dependencies, PostgreSQL client

---

## Common Pitfalls

### 1. Old API Server Process Still Running
**Symptom**: Code changes not reflected, endpoint returns 404
**Fix**: `pkill -9 -f "python.*api_server"` before restarting

### 2. Schema Mismatch Errors
**Symptom**: `column "phone" does not exist` or `column "updated_at" does not exist`
**Cause**: Code referencing columns removed in simplified schema
**Check**: Verify queries in `auth_db.py` and `products.py` match `railway-schema-simple.sql`

### 3. JWT Token Verification Failing
**Symptom**: `Invalid or expired token` even with valid login
**Cause**: Token not being sent with `Authorization: Bearer <token>` header
**Check**: Frontend `api.ts` has `setToken()` called after login

### 4. Railway Build Stuck
**Symptom**: Production endpoints return old version for >10 minutes
**Check**: Railway dashboard for build failures
**Workaround**: Push empty commit `git commit --allow-empty -m "trigger rebuild"`

---

## Database Queries Pattern

### Service Class Pattern (backend/products.py)
```python
class ProductService:
    @staticmethod
    def create_product(db: Session, user_id: str, name: str, ...):
        query = text("""
            INSERT INTO products (id, user_id, name, ...)
            VALUES (:id, :user_id, :name, ...)
            RETURNING *
        """)
        result = db.execute(query, {'id': product_id, 'user_id': user_id, ...})
        db.commit()
        row = result.fetchone()
        return {'id': str(row[0]), 'name': row[2], ...}  # Tuple access!
```

### Endpoint Pattern (api_server.py)
```python
@app.route('/api/products', methods=['POST'])
def create_product():
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1]
    payload = verify_token(token)

    db = next(get_db())
    product = ProductService.create_product(db, payload['user_id'], ...)
    return jsonify({'success': True, 'product': product})
```

---

## Environment Variables

### Required
```bash
DATABASE_URL=postgresql://user:pass@host:port/db
JWT_SECRET_KEY=secret-key-min-32-chars
PORT=5001
```

### Optional
```bash
PYTHONUNBUFFERED=1          # For immediate log output
YOLO_MODEL_PATH=models/yolov8n.pt
DETECTION_CONFIDENCE_THRESHOLD=0.5
```

---

## Phase 2 Features (Planned, Not Implemented)

The system is designed for future expansion:

1. **Training Pipeline** (Phase 2)
   - Upload training images via `/api/training/images`
   - YOLO format annotations via `/api/training/annotations`
   - Export dataset for local training: `/api/training/download-dataset`
   - Upload trained model: `/api/models/upload`

2. **MinIO Storage** (Phase 2)
   - S3-compatible storage on Railway
   - Replace `image_url` TEXT with actual MinIO URLs
   - Install: `boto3` or `minio` Python package

3. **DeepSORT Tracking** (Phase 3)
   - Prevent duplicate counting with track IDs
   - Install: `deep-sort-realtime>=1.3.0`
   - Endpoints: `/api/counting/sessions`, `/api/counting/start-stream`

4. **Human Verification** (Phase 3)
   - Review queue for detections <90% confidence
   - Approve/reject/correct detections
   - Endpoints: `/api/verification/queue`, `/api/verification/<id>/approve`

---

## Project Status (March 2026)

**✅ Complete:**
- Railway PostgreSQL deployment (6 tables)
- JWT authentication (register, login, verify)
- Products CRUD (create, list, update, delete)
- YOLOv8 base model integration
- Local development environment
- Nixpacks build optimization (2-3 min)

**⏳ In Progress:**
- Frontend migration to REST API (partial)
- Railway production deployment

**🔜 Planned:**
- Training images upload
- Annotation system
- Custom YOLO model training
- DeepSORT tracking
- Counting sessions
- Human verification queue
- CSV export
