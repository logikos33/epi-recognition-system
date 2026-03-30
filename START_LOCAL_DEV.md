# 🚀 Setup Desenvolvimento Local

## Por que Desenvolver Local?
- ⚡ Iterações em segundos (não minutos)
- 💰 Economiza horas por dia
- 🐛 Debug mais fácil
- 🔄 Testes rápidos
- 📊 Logs em tempo real

## 🔧 Setup Rápido

### 1. Instalar Dependências

```bash
cd "/Users/vitoremanuel/Documents/Logikos/CATH/Repositorio Reconhecimento de EPI "

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements-api.txt
```

### 2. Configurar Variáveis de Ambiente

```bash
# Criar .env local
cat > .env << EOF
# Database (opcional - pode usar SQLite local)
DATABASE_URL=postgresql://postgres:senha@localhost:5432/epi_recognition

# JWT
JWT_SECRET_KEY=chave-secreta-desenvolvimento-nao-usar-em-prod

# API
PORT=5001
PYTHONUNBUFFERED=1
EOF
```

### 3. Rodar API Local

```bash
# Opção A: Modo desenvolvimento
python api_server.py

# Opção B: Com Gunicorn (produção local)
gunicorn --bind 0.0.0.0:5001 --workers 1 --timeout 120 api_server:app --reload
```

### 4. Testar

```bash
# Health check
curl http://localhost:5001/health

# Registrar usuário
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@local.dev","password":"123456","full_name":"Local Dev"}'
```

## 🔄 Workflow de Desenvolvimento

```
1. Fazer alteração no código
2. Ctrl+C no terminal (parar API)
3. python api_server.py (reiniciar)
4. Testar imediatamente
5. Repetir!
```

Tempo por ciclo: **~5 segundos**

## 📦 Deploy para Produção

Quando estiver satisfeito com o código:

```bash
git add .
git commit -m "feat: Nova funcionalidade X"
git push origin main
```

Railway faz deploy automático (2-3 min).

## 💡 Dicas

### Auto-reload com Flask
```bash
pip install flask==3.0.0

# No final do api_server.py:
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

Com `debug=True`, o Flask recarrega automaticamente ao salvar arquivo!

### Logs Locais
Aparecem direto no terminal - mais fácil que Railway!

### Frontend Local
```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000
API: http://localhost:5001

## ✅ Pronto!
Desenvolva local, deploy só quando estiver perfeito!
