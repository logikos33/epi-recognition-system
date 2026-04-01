# EPI Monitor - Microservices Railway Deploy

## STATUS AUTAL

✅ **CÓDIGO PRONTO**: V2-clean com arquitetura de microserviços  
✅ **FRONTEND BUILDADO**: frontend-new/dist/  
✅ **CONFIGURAÇÃO RAILWAY**: railway.toml, nixpacks.toml, railway_start.py  
✅ **GIT PUSHED**: Tag v1.0.0-staging  

## DEPLOY VIA BROWSER (RECOMENDADO)

### Passo 1: Criar Projeto Novo
1. Acessar: https://railway.com/new
2. Clicar em "Deploy from GitHub repo"
3. Selecionar: `logikos33/epi-recognition-system`
4. Branch: `V2-clean`
5. Nome do projeto: `epi-monitor-microservices`

### Passo 2: Adicionar Serviços

No dashboard do Railway:

#### 2.1 PostgreSQL
- New Service → Database → PostgreSQL
- Railway vai criar automaticamente

#### 2.2 Redis
- New Service → Database → Redis  
- Railway vai criar automaticamente

#### 2.3 API Service
- New Service → Deploy from GitHub repo
- Repo: `logikos33/epi-recognition-system`
- Branch: `V2-clean`
- Root Directory: `/` (raiz)

### Passo 3: Configurar Variáveis de Ambiente (API)

No serviço API, clicar em "Variables" e adicionar:

```bash
SERVICE_TYPE=api
JWT_SECRET_KEY=<gerar-32-hex>
SECRET_KEY=<gerar-32-hex>
CAMERA_SECRET_KEY=<gerar-Fernet-key>
FLASK_ENV=staging
PYTHONUNBUFFERED=1
ADMIN_EMAIL=admin@epimonitor.com
ADMIN_PASSWORD=EpiMonitor@2024!
ADMIN_NAME=Administrador
CORS_ORIGINS=*
```

**Gerar secrets:**
```bash
# JWT Secret
python3 -c "import secrets; print(secrets.token_hex(32))"

# Flask Secret  
python3 -c "import secrets; print(secrets.token_hex(32))"

# Camera Secret
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Passo 4: Deploy

Clicar "Deploy" no serviço API. Railway vai:
1. Detectar nixpacks.toml
2. Instalar dependências (3-5 min)
3. Executar migrations automaticamente
4. Criar admin user
5. Iniciar API

### Passo 5: Worker Service (Opcional - quando tiver câmeras)

Criar novo serviço:
- New Service → Deploy from GitHub repo
- Mesmo repo, branch V2-clean
- Variáveis:
  ```bash
  SERVICE_TYPE=worker
  WORKER_ID=worker-1
  YOLO_MODEL_PATH=storage/models/active/model.pt
  ```
- DATABASE_URL e REDIS_URL são herdados automaticamente

## MONITORAR DEPLOY

```bash
# Após criar projeto via browser, conectar:
cd "/Users/vitoremanuel/Documents/Logikos/CATH/Repositorio Reconhecimento de EPI "
railway link

# Ver status
railway status

# Logs em tempo real
railway logs --tail

# Ver URL
railway domain
```

## TESTAR DEPLOYMENT

```bash
# Aguardar build (3-5 min)
# Testar health
curl https://<seu-projeto>.railway.app/health

# Testar login
curl -X POST https://<seu-projeto>.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@epimonitor.com","password":"EpiMonitor@2024!"}'

# Testar workers health
curl https://<seu-projeto>.railway.app/api/workers/health
```

## ARQUITETURA FINAL

```
┌─────────────────────────────────────────────────┐
│              Railway Project                    │
│                                                 │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │   API Flask  │◄───┤      Redis           │  │
│  │ SERVICE_TYPE │    │   (Event Bus)        │  │
│  │    =api      │◄───┤                      │  │
│  └──────────────┘    └──────────────────────┘  │
│         ▲                     ▲                │
│         │ commands           │ events         │
│         │                     │                │
│  ┌──────┴─────────────────────┴────────┐      │
│  │     Worker (SERVICE_TYPE=worker)    │      │
│  │  FFmpeg + YOLO + Stream Processing  │      │
│  └─────────────────────────────────────┘      │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │         PostgreSQL (Database)           │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## CUSTOS ESTIMADOS

- API Service: ~$10/mês
- PostgreSQL: ~$15/mês  
- Redis: ~$5/mês
- Worker (opcional): ~$40/mês
- **TOTAL SEM CÂMERAS**: ~$30/mês
- **TOTAL COM 1 WORKER**: ~$70/mês

## PRÓXIMOS PASSOS

Após deploy bem-sucedido:

1. ✅ Testar autenticação
2. ✅ Testar endpoints principais
3. ✅ Verificar database migrations
4. ✅ Acessar frontend no browser
5. ⏳ Adicionar Worker quando tiver câmeras RTSP
6. ⏳ Testar streaming YOLO em tempo real

## SOLUÇÃO DE PROBLEMAS

### Build falhou
- Verificar logs: `railway logs --lines 100`
- Verificar se nixpacks.toml está na raiz

### Erro de conexão com banco
- DATABASE_URL está configurada?
- Prefixo postgres:// foi corrigido para postgresql://?

### Redis connection refused
- REDIS_URL está configurada no serviço?
- Serviço Redis foi criado e está online?

### Admin não criado
- Verificar logs por "Admin criado"
- Tabela `users` existe no banco?

