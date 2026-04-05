-- Migration 012: Otimização de storage de vídeos de treinamento
-- Data: 2026-04-02
-- Objetivo: Deduplicação SHA256 + retenção de 7 dias após extração

-- 1. Coluna para deduplicação por hash SHA256
ALTER TABLE training_videos
    ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_training_videos_hash
    ON training_videos(content_hash)
    WHERE content_hash IS NOT NULL;

-- 2. Colunas para controle de retenção (7 dias após extração)
ALTER TABLE training_videos
    ADD COLUMN IF NOT EXISTS frames_extracted_at TIMESTAMP;

ALTER TABLE training_videos
    ADD COLUMN IF NOT EXISTS video_deleted_at TIMESTAMP;

-- 3. Coluna computada para data de auto-delete (7 dias após frames_extracted_at)
ALTER TABLE training_videos
    ADD COLUMN IF NOT EXISTS auto_delete_after TIMESTAMP;

-- 4. Índice para o scheduler de cleanup
CREATE INDEX IF NOT EXISTS idx_videos_cleanup
    ON training_videos(auto_delete_after)
    WHERE video_deleted_at IS NULL
    AND frames_extracted_at IS NOT NULL;

-- Resultado esperado:
-- - content_hash: SHA256 do arquivo para deduplicação
-- - frames_extracted_at: Quando os frames foram extraídos
-- - auto_delete_after: Calculado como frames_extracted_at + 7 dias
-- - Scheduler deleta vídeos onde auto_delete_after < NOW()
