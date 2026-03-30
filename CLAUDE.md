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

**EPI Recognition System** - Sistema de reconhecimento de EPI com streaming HLS em tempo real e detecção YOLO. O sistema suporta 5-12 câmeras IP simultâneas com latência < 3 segundos, contagem automática de produtos e verificação humana.

### Tech Stack
- **Backend**: Flask (Python 3.11) com PostgreSQL no Railway
- **Frontend**: Next.js 14 (TypeScript) com hls.js e socket.io-client
- **Streaming**: FFmpeg para transcodificação RTSP→HLS
- **AI/ML**: YOLOv8 para detecção de objetos em tempo real (5 FPS)
- **WebSocket**: Flask-SocketIO para broadcast de detecções
- **Deployment**: Railway com Nixpacks (2-3 min builds, FFmpeg incluído)
- **Database**: PostgreSQL com schema simplificado (7 tabelas, incluindo ip_cameras)
- **Authentication**: JWT tokens com bcrypt password hashing

### HLS Streaming Features
- **5-12 câmeras IP simultâneas** com fabricantes suportados: Intelbras, Hikvision, Generic ONVIF
- **Latência < 3 segundos** com otimizações FFmpeg (preset ultrafast, segments 1s, playlist 3)
- **Detecção YOLO contínua** a 5 FPS com bounding boxes em tempo real via WebSocket
- **Auto-restart** de streams mortos (máx 3 tentativas)
- **Health monitoring** com relatórios detalhados
- **Error handling avançado** com reconexão automática (exponential backoff)

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

**HLS Streaming Tables** (migrations/002_create_cameras_table.sql):
7. `ip_cameras` - Câmeras IP para streaming HLS (suporta Intelbras, Hikvision, Generic)

---

## HLS Streaming System

### Overview

Sistema completo de streaming HLS com detecção YOLO em tempo real para câmeras IP.

**Arquitetura:**
```
IP Camera (RTSP) → FFmpeg → HLS (m3u8 + ts segments) → Browser (hls.js)
                    ↓
                 YOLO Detection (5 FPS)
                    ↓
              WebSocket (detections)
                    ↓
           Frontend (overlay boxes)
```

### Backend Modules

**IP Camera Service** (`backend/ip_camera_service.py`):
- CRUD completo para câmeras IP
- Auto-geração de URLs RTSP por fabricante
- Mascaramento de senhas em respostas
- Métodos: `create_camera`, `list_cameras_by_user`, `get_camera_by_id`, `update_camera`, `delete_camera`

**RTSP Builder** (`backend/rtsp_builder.py`):
- Gera URLs RTSP específicas por fabricante
- Suporta: Intelbras, Hikvision, Generic ONVIF
- Valida endereço IP e porta

**Stream Manager** (`backend/stream_manager.py`):
- Gerencia processos FFmpeg para HLS
- Health monitoring (30s intervals)
- Auto-restart de streams mortos (máx 3 tentativas)
- Métodos: `start_stream`, `stop_stream`, `get_stream_status`, `get_all_streams_status`, `get_stream_health_report`

**YOLO Processor** (`backend/yolo_processor.py`):
- Detecção contínua em threads (5 FPS padrão)
- Parser de detecções YOLO
- Callback para broadcast via WebSocket
- Graceful shutdown

### API Endpoints

**Autenticação:**
- `POST /api/auth/register` - Registrar usuário
- `POST /api/auth/login` - Login e obter token JWT

**Câmeras IP:**
- `GET /api/cameras` - Listar câmeras do usuário
- `POST /api/cameras` - Criar nova câmera (auto-gera RTSP URL)
- `GET /api/cameras/<id>` - Obter câmera por ID
- `PUT /api/cameras/<id>` - Atualizar câmera
- `DELETE /api/cameras/<id>` - Deletar câmera
- `POST /api/cameras/test` - Testar conectividade RTSP

**Streams HLS:**
- `POST /api/cameras/<id>/stream/start` - Iniciar stream HLS + YOLO
- `POST /api/cameras/<id>/stream/stop` - Parar stream
- `GET /api/cameras/<id>/stream/status` - Status do stream
- `GET /api/streams/status` - Status de todos os streams
- `GET /streams/health` - Health report detalhado (Task 17)
- `GET /streams/<camera_id>/<filename>` - Servir arquivos HLS

### Frontend Components

**HLS Camera Feed** (`frontend/src/components/hls-camera-feed.tsx`):
- Player de vídeo HLS com hls.js
- Reconexão automática (exponential backoff, max 5 tentativas)
- WebSocket para detecções em tempo real
- Canvas overlay para bounding boxes YOLO
- Indicadores visuais de status
- Suporte a Safari (HLS nativo)
- Error handling avançado (Task 17)

**Camera Grid** (`frontend/src/components/camera-grid.tsx`):
- Grid responsivo para 12 câmeras (3 grandes + 9 miniaturas)
- Toggle buttons para seleção
- Estados de loading e error

**Types** (`frontend/src/types/camera.ts`):
- `Camera` - Interface completa de câmera IP
- `Detection` - Payload WebSocket de detecções
- `DetectionBox` - Bounding box com coordenadas
- `StreamStatus` - Status do stream HLS

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# JWT
JWT_SECRET_KEY=secret-key-min-32-chars

# FFmpeg (opcional - têm defaults)
FFMPEG_LOG_LEVEL=warning
FFMPEG_PRESET=ultrafast
FFMPEG_VIDEO_BITRATE=512k
FFMPEG_RESOLUTION=640x360

# HLS (opcional - têm defaults)
HLS_SEGMENT_DURATION=1
HLS_PLAYLIST_SIZE=3

# Health Monitoring (opcional - têm defaults)
STREAM_HEALTH_CHECK_INTERVAL=30
MAX_STREAM_RESTARTS=3
```

### Frontend URL Configuration

Create `.env.local` in frontend directory:
```bash
NEXT_PUBLIC_API_URL=http://localhost:5001
```

For Railway production:
```bash
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

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

## Railway Deployment

### Quick Deploy

```bash
# 1. Push to main branch
git add .
git commit -m "feat: description"
git push origin main

# 2. Railway auto-deploys (2-3 min build)
# FFmpeg is installed automatically via nixpacks.toml

# 3. Check deployment status
railway status

# 4. View logs
railway logs
```

### Environment Variables in Railway

Set these in Railway dashboard:
```bash
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=your-secret-key-min-32-chars
PORT=5001
```

Optional (for FFmpeg tuning):
```bash
FFMPEG_PRESET=ultrafast
FFMPEG_VIDEO_BITRATE=512k
STREAM_HEALTH_CHECK_INTERVAL=30
```

### Monitoring

**Health Endpoints:**
- `GET /health` - System health
- `GET /streams/health` - Streams health report (Task 17)
- `GET /api/streams/status` - All streams status

**Logs:**
```bash
railway logs                    # Real-time logs
railway logs -n 100            # Last 100 lines
railway logs --tail            # Follow logs
```

**Troubleshooting:**
- Check FFmpeg installation: `railway logs | grep ffmpeg`
- High CPU? Reduce quality: `FFMPEG_RESOLUTION=640x360`
- Stream crashes? Check RTSP connectivity

Full guide: `RAILWAY_FFMPEG_CONFIG.md`

---

## HLS Testing

### End-to-End Tests (Task 19)

Run complete E2E test suite:

```bash
# Using test runner (recommended)
./run-e2e-tests.sh

# Using pytest directly
pytest tests/test_e2e_hls_streaming.py -v -s
```

**Test Coverage:**
1. User authentication flow
2. Camera CRUD operations
3. Stream lifecycle (start → status → health → stop)
4. Camera connectivity testing
5. Security validation
6. System health checks

**Prerequisites:**
- API server running on http://localhost:5001
- PostgreSQL database configured
- FFmpeg installed (optional, for stream tests)

### Manual Testing

**1. Test Authentication:**
```bash
# Register
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@local.dev","password":"123456","full_name":"Test"}'

# Login
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@local.dev","password":"123456"}'
```

**2. Create Camera:**
```bash
TOKEN="eyJhbGc..."

curl -X POST http://localhost:5001/api/cameras \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Camera",
    "manufacturer": "intelbras",
    "ip": "192.168.1.100",
    "port": 554,
    "username": "admin",
    "password": "password123"
  }'
```

**3. Start Stream:**
```bash
curl -X POST http://localhost:5001/api/cameras/1/stream/start \
  -H "Authorization: Bearer $TOKEN"
```

**4. Check Status:**
```bash
curl http://localhost:5001/streams/1/stream.m3u8 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting

### Common Issues

**1. API server won't start**
```bash
# Kill old process
pkill -9 -f "python.*api_server"

# Check port 5001
lsof -i :5001

# Restart server
python api_server.py
```

**2. FFmpeg not found**
```bash
# Install FFmpeg
brew install ffmpeg  # macOS

# Verify
ffmpeg -version
```

**3. Stream won't start**
```bash
# Check RTSP connectivity
curl -X POST http://localhost:5001/api/cameras/test \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"manufacturer":"generic","ip":"192.168.1.100","port":554}'

# Check logs
tail -f logs/api_server.log
```

**4. WebSocket not connecting**
```bash
# Check WebSocket handler in api_server.py
# Should see: socketio = SocketIO(...)

# Test WebSocket endpoint
curl http://localhost:5001/ws/test
```

**5. HLS not playing in browser**
```bash
# Check HLS file exists
ls -la streams/1/

# Check HLS content
cat streams/1/stream.m3u8

# Verify hls.js is loaded
# Browser console: check for Hls object
```

### Error Messages

**"401 Unauthorized"**:
- Token expired or missing
- Solution: Login again to get new token

**"Camera not found"**:
- Camera doesn't exist or belongs to different user
- Solution: Check camera ID and ownership

**"Stream failed to start"**:
- FFmpeg crashed or RTSP unreachable
- Solution: Check logs, verify RTSP URL, test connectivity

**"HLS authentication limitation"**:
- Browser limitation, can't send custom headers for HLS
- Solution: Use signed URLs or proxy server (planned)

---

## Project Status (March 2026)

**✅ Complete (Tasks 1-20):**
- ✅ Railway PostgreSQL deployment (7 tabelas incluindo ip_cameras)
- ✅ JWT authentication (register, login, verify)
- ✅ Products CRUD (create, list, update, delete)
- ✅ **HLS Streaming System** (Tasks 1-19) - 100% completo
  - IP camera management (RTSP builder, CRUD)
  - FFmpeg transcoding (StreamManager com health monitoring)
  - YOLO detection contínua (YOLOProcessor)
  - WebSocket real-time (Flask-SocketIO)
  - Frontend HLS player (hls-camera-feed, camera-grid)
  - Error handling avançado (auto-restart, reconexão)
  - Railway FFmpeg config (nixpacks.toml)
  - E2E test suite completo
- ✅ YOLOv8 base model integration
- ✅ Local development environment
- ✅ Nixpacks build optimization (2-3 min)
- ✅ Code quality (15 issues corrigidas)
- ✅ 87 testes passando

**⏳ Deprecated:**
- Frontend migration to REST API (completo)
- Railway production deployment (configurado)

**🔜 Planned (Future Phases):**
- Training images upload
- Annotation system
- Custom YOLO model training
- DeepSORT tracking
- Counting sessions
- Human verification queue
- CSV export
