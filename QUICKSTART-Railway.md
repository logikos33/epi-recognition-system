# EPI Monitor - Railway Deploy QUICKSTART

## 🚀 DEPLOY RÁPIDO (5 minutos)

### 1. Criar Projeto Railway
Acessar: https://railway.com/new

### 2. Selecionar GitHub
- Repo: `logikos33/epi-recognition-system`
- Branch: `V2-clean`
- Clicar "Deploy Now"

### 3. Adicionar Serviços
No dashboard Railway:
- **PostgreSQL**: New Service → Database → PostgreSQL
- **Redis**: New Service → Database → Redis

### 4. Configurar Variáveis (API Service)
Clicar no serviço API → Variables → New Variable:

```
SERVICE_TYPE=api
JWT_SECRET_KEY=<gerar-32-hex>
SECRET_KEY=<gerar-32-hex>
CAMERA_SECRET_KEY=<gerar-32-hex>
FLASK_ENV=staging
PYTHONUNBUFFERED=1
ADMIN_EMAIL=admin@epimonitor.com
ADMIN_PASSWORD=EpiMonitor@2024!
ADMIN_NAME=Administrador
CORS_ORIGINS=*
```

### 5. Deploy
Clicar "Deploy" e aguardar 3-5 minutos.

### 6. Testar
```bash
# Health check
curl https://<seu-projeto>.railway.app/health

# Login
curl -X POST https://<seu-projeto>.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@epimonitor.com","password":"EpiMonitor@2024!"}'
```

---

## 📖 DOCUMENTAÇÃO COMPLETA

Ver `railway-deploy-instructions.md` para documentação detalhada.

---

## 🔧 ADICIONAR WORKER (QUANDO TIVER CÂMERAS)

### 1. Criar Worker Service
New Service → Deploy from GitHub repo
- Mesmo repo, branch V2-clean

### 2. Variáveis Worker
```
SERVICE_TYPE=worker
WORKER_ID=worker-1
YOLO_MODEL_PATH=storage/models/active/model.pt
```

### 3. Deploy
Clicar "Deploy"

---

## 💰 CUSTOS

- API: ~$10/mês
- PostgreSQL: ~$15/mês
- Redis: ~$5/mês
- Worker: ~$40/mês (opcional)

**Total sem câmeras: ~$30/mês**
**Total com 1 worker: ~$70/mês**

---

## 🔑 CREDENCIAIS

- Email: `admin@epimonitor.com`
- Senha: `EpiMonitor@2024!`
