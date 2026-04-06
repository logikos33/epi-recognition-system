# EPI Monitor — Rebuild Spec

## Goal
Complete rebuild of EPI Monitor from monolithic Flask app (3782 lines) to modular Flask Blueprint architecture.

## Tech Stack
- Backend: Flask 3.x, psycopg2 (NO SQLAlchemy), Celery, Redis
- Frontend: Vite + React + TypeScript (frontend-new/)
- Deploy: Railway (nixpacks)
- AI: YOLOv8 (ultralytics)

## Critical Rules
1. CORS: whitelist via CORS_ORIGINS env var, NEVER bare CORS(app)
2. JWT: always validate expiration (exp vs time.time())
3. RTSP URLs: RTSPUrlValidator before ANY URL reaches FFmpeg
4. SQL: parameterized queries, NEVER f-strings with user input
5. PostgreSQL: no "ADD CONSTRAINT IF NOT EXISTS" — use DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$;
6. psycopg2 ThreadedConnectionPool + RealDictCursor (NO SQLAlchemy)
7. ultralytics in BOTH requirements.txt AND requirements-railway.txt
8. No duplicate Flask routes
9. Vite: usePolling: true, cacheDir: '/tmp/vite-cache-epi'
10. image-annotation.tsx: FROZEN — never modify

## Architecture

### Backend: epi-monitor/backend/app/
- Application Factory pattern
- Blueprints per domain: auth, health, videos, annotations, training, cameras
- Each module: routes.py, service.py, repository.py, tasks.py (if async)
- Shared: core/ (exceptions, responses, middleware, auth, circuit_breaker)
- Infrastructure: database/ (connection pool, base_repo, migrations), storage/ (R2), queue/ (celery)

### Frontend: epi-monitor/frontend/
- Vite + React + TypeScript
- Modular: src/modules/{auth,videos,annotations,training,monitoring}/
- Shared: src/shared/{components,hooks,services,types}/
- Error Boundaries per section
- Auth context with JWT expiry validation

## Phases
- Phase 0: Foundation & Structure
- Phase 1: Infrastructure (DB, queue, storage)
- Phase 2: Auth module
- Phase 3: Health module  
- Phase 4: Videos module
- Phase 5: Annotations module
- Phase 6: Training module
- Phase 7: Cameras/Monitoring module
- Phase 8: Frontend
- Phase 9: Tests & Security
- Phase 10: Railway deploy

## Graceful Degradation
- YOLO fail → monitoring degraded, rest works
- Redis fail → RT features degraded, REST works
- Migration fail → log error, continue with existing tables
- R2 fail → return 503, queue retry

## Deploy Requirements
- Commit + push → Railway build → observe logs → ACTIVE status → 3+ min without crash = success
