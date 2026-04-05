# DEPLOY RAILWAY VIA BROWSER - GUIA COMPLETO

**Status Código:** ✅ Pronto (V2-clean atualizada com cache-busting)
**Data:** 1 Abr 2026
**Branch:** V2-clean (staging)

---

## PROBLEMA: Railway CLI falha com "Unauthorized"

Railway CLI tem bugs autenticação para adicionar serviços. Solução: **usar browser interface**.

---

## PASSO 1: Acessar Projeto Railway

1. Abrir: https://railway.app/project/366c8fae-197b-4e55-9ec9-b5261b3f4b62
2. Verificar que está em ambiente **"Pré-Produção"** (dropdown no topo)

---

## PASSO 2: Deletar Serviço Antigo (se existir)

Se houver um serviço "epi-recognition-system" com status de erro:

1. Clicar no serviço
2. Settings → General → Delete Service
3. Confirmar deletação

**Motivo:** Service antigo está sem link correto com o repo. Criar do zero é mais rápido.

---

## PASSO 3: Criar Novo Serviço API

### 3.1 Adicionar Serviço do GitHub

1. Clicar **"New Service"** → **"Deploy from GitHub repo"**
2. Selecionar: **logikos33/epi-recognition-system**
3. Selecionar branch: **V2-clean**
4. Clicar **"Deploy Now"**

### 3.2 Aguardar Build Inicial

- Build vai levar 2-3 minutos
- **Vai FALHAR** (normal - falta DATABASE_URL e REDIS_URL)
- Não se preocupar com erro ainda

---

## PASSO 4: Adicionar PostgreSQL

1. Clicar **"New Service"** → **"Database"** → **"PostgreSQL"**
2. Aguardar criação (~30 segundos)
3. PostgreSQL vai injetar automaticamente `DATABASE_URL` no serviço API

---

## PASSO 5: Adicionar Redis

1. Clicar **"New Service"** → **"Database"** → **"Redis"**
2. Aguardar criação (~30 segundos)
3. Redis vai injetar automaticamente `REDIS_URL` no serviço API

---

## PASSO 6: Configurar Variáveis de Ambiente

No serviço **API** clicar em **"Variables"** → **"New Variable"**:

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
PORT=8080
```

### IMPORTANTE: Conectar PostgreSQL e Redis

1. Na aba Variables do serviço API
2. Procurar seção **"Service Variables"**
3. Clicar em **"Connect Service"** ou **"Add Reference"**
4. Selecionar **PostgreSQL** → vai injetar `DATABASE_URL`
5. Selecionar **Redis** → vai injetar `REDIS_URL`

---

## PASSO 7: Redeploy com Tudo Configurado

1. Clicar na aba **"Deployments"** do serviço API
2. Clicar botão **"Redeploy"** (ícone de refresh)
3. Aguardar build (2-3 minutos)

---

## PASSO 8: Verificar Deploy

### 8.1 Checar Health Check

```bash
curl https://<seu-projeto>-api-epi-monitor.up.railway.app/health
```

Esperado:
```json
{"status": "healthy", "service": "api", "timestamp": "..."}
```

### 8.2 Checar Logs

1. Na aba **"Deployments"**
2. Clicar no deployment mais recente
3. Ver logs:
   - ✅ "✅ PostgreSQL conectado"
   - ✅ "✅ Redis conectado"
   - ✅ "✅ Migrations executadas"
   - ✅ "✅ Admin criado: admin@epimonitor.com"
   - ✅ "✅ Starting API server on port 8080"

### 8.3 Testar Login

```bash
curl -X POST https://<seu-projeto>-api.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@epimonitor.com","password":"EpiMonitor@2024!"}'
```

Esperado:
```json
{
  "access_token": "eyJ...",
  "user": {...}
}
```

---

## PASSO 9: Acessar Frontend

Railway vai gerar uma URL pública para o frontend:

1. Clicar no serviço API
2. Aba **"Settings"** → **"Networking"**
3. URL gerada: **https://<seu-projeto>-api.up.railway.app**

Frontend React é servido de `/dist/index.html`

---

## PASSO 10: (OPCIONAL) Adicionar Worker

**Só adicionar quando tiver câmeras IP conectadas!**

### 10.1 Criar Worker Service

1. Clicar **"New Service"** → **"Deploy from GitHub repo"**
2. Mesmo repo: **logikos33/epi-recognition-system**
3. Branch: **V2-clean**
4. Deploy

### 10.2 Configurar Worker Variables

```
SERVICE_TYPE=worker
WORKER_ID=worker-1
YOLO_MODEL_PATH=storage/models/active/model.pt
PORT=8080
```

### 10.3 Conectar Redis

1. Service Variables → Connect Service → **Redis**
2. Redeploy

---

## VALIDAÇÃO FINAL

### Checklist

- [ ] PostgreSQL service criado
- [ ] Redis service criado
- [ ] API service com V2-clean branch
- [ ] DATABASE_URL injetado via PostgreSQL
- [ ] REDIS_URL injetado via Redis
- [ ] Todas as vars configuradas
- [ ] Health check retorna 200
- [ ] Login funciona
- [ ] Dashboard acessível
- [ ] Sem erros 500 nos logs

### Testes End-to-End

```bash
# 1. Health check
curl https://<projeto>.up.railway.app/health

# 2. Login
TOKEN=$(curl -s -X POST https://<projeto>.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@epimonitor.com","password":"EpiMonitor@2024!"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

# 3. Dashboard KPIs
curl https://<projeto>.up.railway.app/api/dashboard/kpis \
  -H "Authorization: Bearer $TOKEN"

# 4. Câmeras (lista vazia ok)
curl https://<projeto>.up.railway.app/api/cameras \
  -H "Authorization: Bearer $TOKEN"

# 5. Workers health
curl https://<projeto>.up.railway.app/api/workers/health \
  -H "Authorization: Bearer $TOKEN"
```

---

## CUSTOS ESTIMADOS

- API: ~$10/mês
- PostgreSQL: ~$15/mês
- Redis: ~$5/mês
- Worker: ~$40/mês (opcional, só quando tiver câmeras)

**Total sem câmeras: ~$30/mês**
**Total com 1 worker: ~$70/mês**

---

## TROUBLESHOOTING

### Erro: "DATABASE_URL : AUSENTE"

**Causa:** PostgreSQL não conectado ao serviço API

**Solução:**
1. Clicar no serviço API
2. Variables → Service Variables → Connect Service
3. Selecionar PostgreSQL

### Erro: "No module named 'sqlalchemy'"

**Causa:** Build cache antigo

**Solução:**
1. Deletar serviço
2. Criar novo (passo 3)
3. Dockerfile com CACHE_BUST vai forçar rebuild limpo

### Erro: "relation does not exist"

**Causa:** Migrations não rodaram

**Solução:**
1. Verificar logs do deployment
2. Procurar "✅ Migrations executadas"
3. Se não aparecer, ver `railway_start.py` linha 40-80

### Erro: "Unauthorized no browser"

**Causa:** Sessão expirada

**Solução:**
1. Logout do Railway
2. Login novamente
3. Tentar criar serviço

---

## URL ÚTEIS

- **Projeto:** https://railway.app/project/366c8fae-197b-4e55-9ec9-b5261b3f4b62
- **Dashboard:** https://railway.app
- **Docs:** https://docs.railway.app

---

## PRÓXIMO PASSOS (pós-deploy)

1. **Testar frontend:** Acessar URL gerada, fazer login
2. **Adicionar câmera:** Usar wizard no frontend
3. **Iniciar stream:** Clicar em "Play" na câmera
4. **Ver detecções:** WebSocket deve mostrar boxes YOLO
5. **Criar regras:** Dashboard → Regras → Adicionar
6. **Exportar dados:** Dashboard → Exportar Excel

---

*Gerado: 2026-04-01*
*Autor: Claude Sonnet 4.5*
*Contexto: Deploy V2-clean com microservices + cache-bust*
