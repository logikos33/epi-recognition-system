-- Desabilitar confirmação de email para permitir login imediato
-- Execute isso no Supabase SQL Editor

-- Opção 1: Alterar configuração de autenticação (não funciona via SQL)
-- Você precisa fazer isso via dashboard do Supabase

-- Opção 2: Desabilitar RLS temporariamente para testes
ALTER TABLE auth.users DISABLE ROW LEVEL SECURITY;

-- Opção 3: Atualizar usuários existentes para confirmados
UPDATE auth.users
SET email_confirmed_at = NOW()
WHERE email_confirmed_at IS NULL;

-- Nota: A melhor opção é desabilitar via Dashboard do Supabase:
-- Authentication → Settings → Enable email confirmation = OFF
