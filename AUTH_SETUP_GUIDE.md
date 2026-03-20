# 🔐 Guia de Setup - Autenticação e Banco de Dados

## Passo 1: Criar Projeto Supabase

### 1.1 Acessar Supabase
1. Acesse: https://supabase.com
2. Clique em **"Start your project"**
3. Faça login com GitHub ou Google

### 1.2 Criar Novo Projeto
1. Clique em **"New Project"**
2. Preencha:
   - **Name:** `epi-recognition-system`
   - **Database Password:** (crie uma senha segura e salve!)
   - **Region:** Escolha `South America (São Paulo)` ou mais próximo
3. Clique em **"Create new project"**
4. Aguarde 2-3 minutos para o projeto ser criado

---

## Passo 2: Configurar Banco de Dados

### 2.1 Executar Schema SQL
1. No dashboard do Supabase, clique em **"SQL Editor"** no menu lateral
2. Clique em **"New Query"**
3. **Copie o conteúdo do arquivo** `supabase-schema.sql`
4. Cole no editor SQL
5. Clique em **"Run"** ou pressione `Ctrl+Enter`
6. Veja se aparece "Success" no rodapé

### 2.2 Verificar Tabelas Criadas
1. Clique em **"Table Editor"** no menu lateral
2. Deve ver as tabelas:
   - `users`
   - `cameras`
   - `detections`
   - `alerts`
   - `sessions`

---

## Passo 3: Obter Credenciais Supabase

### 3.1 Obter API URL e Key
1. No dashboard do Supabase, clique em **"Settings"** (icone de ⚙️)
2. Clique em **"API"**
3. Copie:
   - **Project URL:** algo como `https://xxxxx.supabase.co`
   - **anon/public key:** a "public" key

### 3.2 Obter Database Connection String
1. Ainda em **Settings**, clique em **"Database"**
2. Procure por **"Connection string"**
3. Clique em **"URI"**
4. Copie a connection string (algo como):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

---

## Passo 4: Configurar Railway com Nova API

### 4.1 Atualizar Railway
**IMPORTANTE:** Vamos substituir o API server atual pela versão com autenticação.

1. Acesse seu projeto no Railway: https://railway.com/project/...
2. Vá em **Settings** → **Variables**
3. Adicione as variáveis de ambiente:

   ```
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   JWT_SECRET_KEY=sua-chave-secreta-super-segura-aqui
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=your-anon-key-here
   ```

4. Mude o **Start Command** para:
   ```
   python api_server_full.py
   ```

5. Clique em **"Deploy"** para fazer redeploy

---

## Passo 5: Testar Autenticação

### 5.1 Testar Registro
```bash
curl -X POST https://epi-recognition-system-production.up.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "full_name": "Test User",
    "company_name": "Test Company"
  }'
```

**Resposta esperada:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "token": "eyJhbGc...",
  "user": {...}
}
```

### 5.2 Testar Login
```bash
curl -X POST https://epi-recognition-system-production.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'
```

### 5.3 Testar Endpoint Protegido
```bash
curl -X GET https://epi-recognition-system-production.up.railway.app/api/auth/me \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

---

## Passo 6: Atualizar Frontend

### 6.1 Instalar Dependências de Auth
No frontend, vamos adicionar:
- React Context para autenticação
- Hooks de autenticação
- Páginas de login/ signup funcionais

### 6.2 Variáveis de Ambiente
No Vercel, adicionar:
```
NEXT_PUBLIC_API_URL=https://epi-recognition-system-production.up.railway.app
```

---

## ✅ Checklist

- [ ] Criar projeto Supabase
- [ ] Executar schema SQL
- [ ] Copiar credenciais (URL, keys)
- [ ] Configurar Railway com variáveis de ambiente
- [ ] Mudar start command para `api_server_full.py`
- [ ] Fazer deploy no Railway
- [ ] Testar registro de usuário
- [ ] Testar login
- [ ] Testar endpoint protegido
- [ ] Atualizar frontend com auth

---

## 🚀 Próximos Passos

Após configurar o backend:

1. **Implementar frontend auth** (páginas de login/ signup)
2. **Criar UI de histórico de detecções**
3. **Adicionar gestão de câmeras**
4. **Testar integração completa**

---

## 📞 Suporte

Se der erro em algum passo, me mande:
1. Screenshot do erro
2. Logs do Railway
3. Mensagem de erro completa

Vou corrigir imediatamente! 🚀
