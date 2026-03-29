# 🔧 Como Criar Tabelas no Railway - Passo a Passo

## 📋 Pré-requisitos
- Projeto Railway acessível
- Serviço PostgreSQL rodando

---

## 🚀 PASSO A PASSO

### 1️⃣ ABRIR DASHBOARD RAILWAY

```
https://railway.app/project/366c8fae-197b-4e55-9ec9-b5261b3f4b62
```

---

### 2️⃣ SELECIONAR SERVIÇO POSTGRESQL

**No dashboard:**
- Clique no serviço **PostgreSQL** (ou "Banco Reconhecimento")
- Vai abrir a página do serviço

---

### 3️⃣ ABRIR QUERY EDITOR

**No serviço PostgreSQL, procure:**
- Aba chamada **"Query"** ou **"Query Editor"**
- Ou botão **"New Query"** ou **"Open Query Editor"**

---

### 4️⃣ COPIAR E COLAR O SCHEMA

**Copie todo o conteúdo do arquivo:** `railway-schema-simple.sql`

**Cole no Query Editor**

Ou copie aqui:

```sql
-- Habilitar extensão UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- TABELA: USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    company_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- TABELA: PRODUCTS
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) UNIQUE,
    category VARCHAR(100),
    description TEXT,
    detection_threshold FLOAT DEFAULT 0.85,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TABELA: TRAINING_IMAGES
CREATE TABLE IF NOT EXISTS training_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    image_url TEXT NOT NULL,
    is_annotated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TABELA: COUNTING_SESSIONS
CREATE TABLE IF NOT EXISTS counting_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vehicle_id VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_products INTEGER DEFAULT 0
);

-- TABELA: COUNTED_PRODUCTS
CREATE TABLE IF NOT EXISTS counted_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES counting_sessions(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    confidence FLOAT NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TABELA: SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ÍNDICES
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_training_images_product_id ON training_images(product_id);
CREATE INDEX IF NOT EXISTS idx_counted_products_session_id ON counted_products(session_id);
```

---

### 5️⃣ EXECUTAR O SQL

**No Query Editor:**
- Clique no botão **"Run"** ou **"Execute"** ou ▶️
- Aguarde alguns segundos

---

### 6️⃣ VERIFICAR SE FUNCIONOU

**No Query Editor, execute:**

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

**Deve aparecer:**
```
- counted_products
- counting_sessions
- products
- sessions
- training_images
- users
```

---

### 7️⃣ REINICIAR SERVIÇO PYTHON

**No dashboard Railway:**
1. Clique no serviço **Python API**
2. Clique em **"Restart"** ou **"Redeploy"**
3. Aguarde 2-3 minutos

---

## ✅ TESTAR

### Testar 1: Health
```bash
curl https://epi-recognition-system-production.up.railway.app/health
```

### Testar 2: Registrar Usuário
```bash
curl -X POST https://epi-recognition-system-production.up.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@example.com","password":"123456","full_name":"Teste"}'
```

**Deve retornar:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "token": "...",
  "user": {...}
}
```

---

## 🔧 SOLUÇÃO DE PROBLEMAS

### Erro: "relation does not exist"
→ Execute o schema novamente

### Erro: "extension uuid-ossp does not exist"
→ Já está tratado com IF NOT EXISTS

### Query Editor não aparece
→ Procure por "Connect", "Console", ou abra diretamente pelo URL do serviço

---

## 📊 ESTRUTURA DAS TABELAS

### users
- id (UUID)
- email (único)
- password_hash
- full_name
- company_name
- created_at
- is_active

### products
- id (UUID)
- user_id (FK → users)
- name
- sku (único)
- category
- description
- detection_threshold
- is_active
- created_at

### training_images
- id (UUID)
- user_id (FK → users)
- product_id (FK → products)
- image_url
- is_annotated
- created_at

### counting_sessions
- id (UUID)
- user_id (FK → users)
- vehicle_id
- status
- started_at
- total_products

### counted_products
- id (UUID)
- session_id (FK → counting_sessions)
- product_id (FK → products)
- confidence
- detected_at

### sessions
- id (UUID)
- user_id (FK → users)
- token (único)
- expires_at
- created_at

---

## 🎯 PRONTO!

Após executar o schema e reiniciar a API, tudo deve funcionar!

**Sucesso!** 🚀
