# 🚀 Deploy no Railway - Guia Completo

Este guia irá ajudá-lo a fazer deploy do sistema EPI Recognition na plataforma Railway.

## 📋 Pré-requisitos

1. **Conta no Railway** - Crie em https://railway.app/
2. **Railway CLI** - Instale com: `npm install -g @railway/cli`
3. **Git** - Repositório configurado

---

## 🔧 Passo 1: Instalar Railway CLI

```bash
# Instalar Railway CLI globalmente
npm install -g @railway/cli

# Verificar instalação
railway --version

# Fazer login
railway login
```

---

## 📦 Passo 2: Preparar o Projeto

### Opção A: Usar o script automatizado

```bash
# Executar script de deploy
chmod +x deploy-railway.sh
./deploy-railway.sh
```

### Opção B: Deploy manual

```bash
# Navegar até o diretório raiz do projeto
cd "Repositorio Reconhecimento de EPI"

# Inicializar projeto Railway
railway init

# Linkar projeto existente (se já tiver um)
railway link
```

---

## 🗄️ Passo 3: Configurar Banco de Dados PostgreSQL

```bash
# Adicionar serviço PostgreSQL
railway add postgresql

# Aguardar database ficar pronto
# O Railway irá criar automaticamente a variável DATABASE_URL
```

### Executar schema do banco de dados

```bash
# Obter DATABASE_URL
railway variables

# Copiar a URL e executar:
psql <DATABASE_URL> < railway-database-schema.sql

# Exemplo:
# psql postgresql://postgres:senha@host.railway.app:5432/railway < railway-database-schema.sql
```

---

## ⚙️ Passo 4: Configurar Variáveis de Ambiente

```bash
# Gerar chave JWT secreta
openssl rand -hex 32

# Definir variáveis de ambiente
railway variables set JWT_SECRET_KEY=<sua-chave-aqui>
railway variables set PORT=5001
railway variables set PYTHONUNBUFFERED=1

# Listar todas as variáveis
railway variables
```

### Variáveis obrigatórias:
- ✅ `DATABASE_URL` - Criado automaticamente pelo Railway PostgreSQL
- ✅ `JWT_SECRET_KEY` - Chave secreta para JWT tokens (gere com `openssl rand -hex 32`)
- ✅ `PORT` - Porta do servidor (default: 5001)

---

## 🚀 Passo 5: Deploy

```bash
# Fazer upload e deploy
railway up

# Ver status do deploy
railway status

# Ver logs em tempo real
railway logs

# Quando o deploy terminar, obter a URL pública
railway domain
```

---

## ✅ Passo 6: Verificar Deploy

```bash
# Testar health check
curl https://seu-projeto.railway.app/health

# Resposta esperada:
# {
#   "status": "healthy",
#   "yolo_loaded": true,
#   "version": "2.0.0"
# }

# Testar registro de usuário
curl -X POST https://seu-projeto.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"123456","full_name":"Test User"}'
```

---

## 🌐 Passo 7: Configurar Frontend

### Atualizar `.env.local` no frontend:

```bash
cd frontend

# Criar arquivo .env.local
cat > .env.local << EOL
NEXT_PUBLIC_API_URL=https://seu-projeto-backend.railway.app
EOL

# Deploy frontend na Vercel
vercel --prod
```

---

## 🔍 Monitoramento e Debug

```bash
# Ver status dos serviços
railway status

# Ver logs
railway logs

# Ver logs de serviço específico
railway logs --service <nome-do-serviço>

# Abrir dashboard no navegador
railway open

# Ver métricas e uso
railway metrics
```

---

## 📊 Estrutura de Serviços no Railway

Após o deploy completo, você terá:

```
epi-recognition-system (Railway Project)
├── 🐍 Python API (api_server_full.py)
│   ├── URL: https://xxx.railway.app
│   ├── Port: 5001
│   └── Health: /health
│
└── 🗄️ PostgreSQL Database
    ├── DATABASE_URL (auto-generated)
    ├── Port: 5432
    └── Tables: 13 (schema completo)
```

---

## 🛠️ Comandos Úteis

```bash
# Listar todos os projetos
railway projects

# Trocar de projeto
railway switch

# Remover serviço
railway remove

# Re-deploy após alterações
git add .
git commit -m "Update"
git push
railway up

# Limpar logs
railway logs --clean

# Derrubar serviço (destrói tudo!)
railway destroy
```

---

## ⚠️ Troubleshooting

### Erro: "Module not found"
```bash
# Verificar se requirements-api.txt está completo
# Re-deploy com:
railway up --verbose
```

### Erro: "Database connection failed"
```bash
# Verificar DATABASE_URL
railway variables

# Testar conexão localmente
psql $DATABASE_URL
```

### Erro: "Health check failing"
```bash
# Ver logs
railway logs

# Ver se porta está correta
railway variables set PORT=5001
```

### Deploy muito lento
```bash
# O build pode demorar no primeiro deploy
# Baixar modelo YOLO pesa ~6MB
# Seja paciente, builds subsequentes são mais rápidos
```

---

## 💰 Custos

Railway oferece:
- **Plano Free**: $5 crédito/mês (suficiente para desenvolvimento)
- **Plano Hobby**: $5/mês (produção recomendado)
- **Plano Pro**: $20/mês (alta disponibilidade)

Estimativa para este projeto:
- Python API: ~$5/mês
- PostgreSQL: ~$5/mês
- **Total**: ~$10/mês

---

## 📚 Próximos Passos

Após o deploy bem-sucedido:

1. ✅ Teste os endpoints de autenticação
2. ✅ Configure o frontend com a URL da API
3. ✅ Faça deploy do frontend na Vercel
4. ✅ Teste o fluxo completo (login → produtos → detecção)
5. ✅ Configure MinIO para armazenamento (Fase 2)
6. ✅ Implemente pipeline de treinamento (Fase 2)

---

## 🔗 Links Úteis

- Railway Dashboard: https://railway.app/
- Railway Docs: https://docs.railway.app/
- PostgreSQL on Railway: https://docs.railway.app/postgres
- Python on Railway: https://docs.railway.app/deploy/python

---

**Última atualização**: 26/03/2026
**Versão**: 1.0 - Deploy Inicial
