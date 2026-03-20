# 🚀 Deploy no Render - Passo a Passo

## 📋 Pré-requisitos
- ✅ Código já está no GitHub
- ✅ requirements.txt atualizado
- ✅ render.yaml criado

---

## 🎯 Passo 1: Acessar o Render

1. **Acessar:** https://render.com
2. **Fazer login** com GitHub (autorize o repositório)

---

## 🎯 Passo 2: Criar Novo Web Service

1. Clique em **"New +"** (botão no canto superior direito)
2. Selecione **"Web Service"**
3. **Conectar GitHub:**
   - Clique em **"Connect GitHub"**
   - Autorize acesso ao repositório `logikos33/epi-recognition-system`
   - Selecione o repositório

---

## 🎯 Passo 3: Configurar o Web Service

### Nome e Branch
- **Name:** `epi-recognition-api`
- **Branch:** `main`
- **Root Directory:** `/` (raiz do projeto)

### Build & Deploy
```
Build Command:  pip install -r requirements.txt
Start Command:  python api_server.py
```

### Environment
- **Runtime:** `Python 3`
- **Region:** Mais próxima de você (ex: Oregon, São Paulo)

### Instância (Plano Gratuito)
- **Type:** `Free`
- **RAM:** 512 MB (suficiente para YOLOv8n)

---

## 🎯 Passo 4: Environment Variables (Opcional)

Adicionar variáveis de ambiente se necessário:

```
PYTHON_VERSION=3.14.0
PORT=5001
FLASK_ENV=production
```

**OU** usar o `render.yaml` que já criamos!

---

## 🎯 Passo 5: Deploy!

Clique em **"Create Web Service"**

O Render vai:
1. Clonar seu repositório
2. Instalar dependências (`pip install -r requirements.txt`)
3. Baixar modelo YOLO automaticamente
4. Iniciar o servidor

**Tempo estimado:** 5-10 minutos

---

## ✅ Verificar Deploy

### Logs do Deploy
1. No painel do serviço, clique em **"Logs"**
2. Deve ver:
   ```
   ✅ YOLO service initialized successfully
   🚀 Starting API server on port 5001
   ```

### Testar API
Quando o deploy terminar, você terá uma URL como:
```
https://epi-recognition-api.onrender.com
```

Teste:
```bash
curl https://epi-recognition-api.onrender.com/health
```

Deve retornar:
```json
{
  "status": "healthy",
  "yolo_loaded": true
}
```

---

## 🔧 Solução de Problemas

### Problema 1: Build falha
**Erro:** `ModuleNotFoundError: No module named 'flask'`

**Solução:**
```bash
# Verifique se requirements.txt tem Flask
grep -i flask requirements.txt

# Deve mostrar:
# flask==3.0.0
# flask-cors==4.0.0
```

### Problema 2: YOLO não carrega
**Erro:** `Failed to load YOLO model`

**Solução:**
O modelo está em `/app/models/yolov8n.pt`
- Na primeira execução, YOLO baixa o modelo automaticamente
- Verifique nos logs se o download concluiu

### Problema 3: API lenta
**Causa:** Instância gratuita (512 MB RAM)

**Solução:**
- Fazer deploy do modelo YOLOv8n (menor)
- Aumentar RAM (plano pago)
- Ou otimizar código para carregar modelo uma vez só

---

## 🎯 Passo 6: Atualizar Frontend

Após o deploy no Render, você terá a URL da API.

**Exemplo:** `https://epi-recognition-api.onrender.com`

Atualizar o frontend:

1. Abrir arquivo: `frontend/src/components/camera-feed.tsx`

2. Procurar linha:
   ```typescript
   const response = await fetch('http://localhost:5001/api/detect', {
   ```

3. Trocar para:
   ```typescript
   const response = await fetch('https://SEU-API.onrender.com/api/detect', {
   ```

4. Commit e push:
   ```bash
   git add .
   git commit -m "chore: Update API URL to Render"
   git push origin main
   ```

5. O Vercel vai fazer deploy automático!

---

## 📱 Passo 7: Testar no Celular

1. **Acessar URL do Vercel** (seu projeto Vercel)
2. **Abrir no navegador do celular**
3. **Ir para:** `/dashboard/live`
4. **Conceder permissão de câmera**
5. **Testar detecção YOLO!** 🎯

---

## 🎉 Sucesso!

Parabéns! Seu sistema está:
- ✅ Backend rodando no Render
- ✅ Frontend rodando no Vercel
- ✅ Acessível de qualquer dispositivo
- ✅ YOLO detectando objetos em tempo real

---

## 📊 URLs Finais

```
Frontend: https://seu-projeto.vercel.app
Backend:  https://epi-recognition-api.onrender.com
API Docs: https://epi-recognition-api.onrender.com/api/test
```

**Boa sorte!** 🚀📱
