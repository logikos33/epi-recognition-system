# 🚀 Deploy no Railway - Guia Rápido

## Status Atual do Projeto
- **URL**: https://epi-recognition-system-production.up.railway.app
- **Versão Atual**: API básica (sem PostgreSQL)
- **Versão Nova**: API completa com PostgreSQL + Auth + Products

## Comandos para Executar (no SEU terminal)

### 1️⃣ Verificar Login
```bash
railway whoami
```
✅ Deve mostrar seu email/usuario

### 2️⃣ Conectar ao Projeto
```bash
railway link 366c8fae-197b-4e55-9ec9-b5261b3f4b62
```
✅ Deve mostrar "Linked to project..."

### 3️⃣ Ver Status
```bash
railway status
```
✅ Mostra serviços do projeto

### 4️⃣ Ver/Adicionar PostgreSQL
```bash
# Ver se já tem
railway services

# Se não tiver PostgreSQL:
railway add postgresql
```

### 5️⃣ Configurar Variáveis
```bash
railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set PORT=5001
railway variables set PYTHONUNBUFFERED=1
```

### 6️⃣ Deploy
```bash
railway up
```

### 7️⃣ Monitorar
```bash
railway logs
```

## Após Deploy Sucesso

### 1. Configurar Banco de Dados
```bash
# Obter DATABASE_URL
railway variables

# Executar schema (substitua <URL>)
psql <URL> < railway-database-schema.sql
```

### 2. Testar API
```bash
curl https://epi-recognition-system-production.up.railway.app/health
```

### 3. Testar Registro
```bash
curl -X POST https://epi-recognition-system-production.up.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"123456","full_name":"Test User"}'
```

### 4. Configurar Frontend
```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=https://epi-recognition-system-production.up.railway.app" > .env.local
```

## Troubleshooting

### Login não funciona
- Abra o navegador quando aparecer
- Ou use: https://railway.app/account/api-tokens

### Erro de build
- Ver logs: `railway logs`
- Veja se requirements-api.txt está completo

### Erro de database
- Verifique se PostgreSQL foi adicionado
- Execute o schema novamente

## Links Úteis
- Dashboard: https://railway.app/project/366c8fae-197b-4e55-9ec9-b5261b3f4b62
- Database: Na aba "PostgreSQL" do projeto
- Logs: `railway logs` ou no dashboard
