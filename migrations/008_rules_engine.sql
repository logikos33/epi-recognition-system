-- Migration 008: Rules Engine for EPI Monitor
-- Tabelas para sistema de regras de negócio e log de eventos de sessão

-- Primeiro, adicionar colunas faltantes à tabela counting_sessions existente
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS camera_id UUID;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS bay_id VARCHAR(50);
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS truck_plate VARCHAR(20);
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS product_class_id INTEGER;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS product_count INTEGER DEFAULT 0;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS ai_count INTEGER DEFAULT 0;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS operator_count INTEGER;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS duration_seconds INTEGER;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS validated_by VARCHAR(100);
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS validated_at TIMESTAMP;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS validation_notes TEXT;
ALTER TABLE counting_sessions ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Tabela de regras de negócio
CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    template_type VARCHAR(50),  -- product_count, bay_control, plate_capture, epi_compliance
    event_type VARCHAR(50) NOT NULL,  -- detection, no_detection, session_start, session_end
    event_config JSONB NOT NULL DEFAULT '{}',
    -- ex: {"class_name": "caminhao", "min_confidence": 0.6}
    action_type VARCHAR(50) NOT NULL,  -- start_session, end_session, count_product, associate_plate, alert
    action_config JSONB NOT NULL DEFAULT '{}',
    -- ex: {"bay_id": "baia_1", "cooldown_seconds": 3}
    camera_ids UUID[],  -- null = todas as câmeras
    cooldown_seconds INTEGER DEFAULT 0,
    min_confidence FLOAT DEFAULT 0.5,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de eventos de sessão (log de eventos)
CREATE TABLE IF NOT EXISTS session_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- detection, count, plate_captured, session_started, session_ended
    class_name VARCHAR(100),
    confidence FLOAT,
    details JSONB DEFAULT '{}',
    occurred_at TIMESTAMP DEFAULT NOW()
);

-- Templates pré-configurados inseridos automaticamente
INSERT INTO rules (name, description, template_type, event_type, event_config, action_type, action_config, is_active)
VALUES
(
    'Controle de Baia — Início',
    'Quando caminhão é detectado, inicia sessão de contagem',
    'bay_control',
    'detection',
    '{"class_name": "caminhao", "min_confidence": 0.6}',
    'start_session',
    '{"cooldown_seconds": 30}',
    TRUE
),
(
    'Controle de Baia — Fim',
    'Quando baia fica vazia por 30s, encerra sessão',
    'bay_control',
    'no_detection',
    '{"class_name": "caminhao", "absence_seconds": 30}',
    'end_session',
    '{}',
    TRUE
),
(
    'Contagem de Produtos',
    'Conta cada produto detectado com cooldown de 3s',
    'product_count',
    'detection',
    '{"class_name": "produto", "min_confidence": 0.7}',
    'count_product',
    '{"cooldown_seconds": 3}',
    TRUE
),
(
    'Captura de Placa',
    'Associa placa detectada à sessão ativa da baia',
    'plate_capture',
    'detection',
    '{"class_name": "placa", "min_confidence": 0.8}',
    'associate_plate',
    '{}',
    TRUE
)
ON CONFLICT DO NOTHING;

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_rules_active ON rules(is_active);
CREATE INDEX IF NOT EXISTS idx_rules_template ON rules(template_type);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON counting_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_camera ON counting_sessions(camera_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON counting_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_events_session ON session_events(session_id);
CREATE INDEX IF NOT EXISTS idx_session_events_time ON session_events(occurred_at DESC);
