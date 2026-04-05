-- Migration 011: Remove regras duplicadas e adicionar unique constraint
-- Data: 2026-04-02
-- Objetivo: Remover regras duplicadas (mesmo user_id e name)

-- 1. Criar backup da tabela
DROP TABLE IF EXISTS rules_backup_20260402;
CREATE TABLE rules_backup_20260402 AS
SELECT * FROM rules;

-- 2. Mostrar estatísticas antes
DO $$
DECLARE
    total_antes INTEGER;
    total_depois INTEGER;
    duplicatas INTEGER;
BEGIN
    SELECT count(*) INTO total_antes FROM rules;
    RAISE NOTICE 'Total de regras antes: %', total_antes;

    -- Contar duplicatas
    SELECT count(*) INTO duplicatas FROM (
        SELECT user_id, name, COUNT(*) as qty
        FROM rules
        GROUP BY user_id, name
        HAVING COUNT(*) > 1
    ) dup;

    RAISE NOTICE 'Conjuntos de regras duplicadas: %', duplicatas;
END $$;

-- 3. Deletar duplicatas (manter a mais recente de cada user_id, name)
DELETE FROM rules
WHERE id IN (
    SELECT id FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY user_id, name
                   ORDER BY created_at DESC
               ) as rn
        FROM rules
    ) ranked
    WHERE rn > 1
);

-- 4. Mostrar estatísticas depois
DO $$
DECLARE
    total_depois INTEGER;
    total_antes INTEGER;
BEGIN
    SELECT count(*) INTO total_depois FROM rules;
    RAISE NOTICE 'Total de regras depois: %', total_depois;

    SELECT count(*) INTO total_antes FROM rules_backup_20260402;
    RAISE NOTICE 'Regras removidas: %', total_antes - total_depois;
END $$;

-- 5. Adicionar unique constraint para prevenir futuras duplicatas
DO $$
BEGIN
    ALTER TABLE rules
    ADD CONSTRAINT rules_user_name_unique
    UNIQUE (user_id, name);
EXCEPTION
    WHEN duplicate_table THEN null;
END $$;

-- 6. Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_rules_user_id
    ON rules(user_id);

CREATE INDEX IF NOT EXISTS idx_rules_name
    ON rules(name);

-- Resultado esperado:
-- - Backup criado em rules_backup_20260402
-- - Duplicatas removidas
-- - Unique constraint (user_id, name) adicionado
-- - Índices criados
