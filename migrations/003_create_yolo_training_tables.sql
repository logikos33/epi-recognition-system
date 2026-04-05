-- Migrations para gerenciamento de classes YOLO e treinamento
-- Executar em ordem: 001, 002, 003, 004

-- ============================================
-- 001_create_classes_yolo_table.sql
-- ============================================

CREATE TABLE IF NOT EXISTS classes_yolo (
  id              SERIAL PRIMARY KEY,
  nome            VARCHAR(100) NOT NULL UNIQUE,
  descricao       TEXT,
  valor_unitario  DECIMAL(10,2) DEFAULT 0.00,
  unidade         VARCHAR(20) DEFAULT 'unidade',
  cor_hex         VARCHAR(7) DEFAULT '#00FF00',
  ativo           BOOLEAN DEFAULT true,
  class_index     INTEGER UNIQUE,
  criado_em       TIMESTAMP DEFAULT NOW(),
  atualizado_em   TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE classes_yolo IS 'Classes configuráveis para detecção YOLO';
COMMENT ON COLUMN classes_yolo.valor_unitario IS 'Valor por unidade detectada para cálculo automático';
COMMENT ON COLUMN classes_yolo.class_index IS 'Índice usado no modelo YOLO (0, 1, 2...)';
COMMENT ON COLUMN classes_yolo.cor_hex IS 'Cor do bounding box no painel (formato hex #RRGGBB)';

-- Insere classes padrão se tabela estiver vazia
INSERT INTO classes_yolo (nome, descricao, valor_unitario, unidade, cor_hex, class_index)
VALUES
  ('EPI_Capacete', 'Equipamento de Proteção Individual - Capacete', 25.00, 'unidade', '#00FF00', 0),
  ('EPI_Luva', 'Equipamento de Proteção Individual - Luva', 8.50, 'unidade', '#FF0000', 1),
  ('EPI_Colete', 'Equipamento de Proteção Individual - Colete', 45.00, 'unidade', '#0000FF', 2)
ON CONFLICT DO NOTHING;

-- ============================================
-- 002_create_contagens_table.sql
-- ============================================

CREATE TABLE IF NOT EXISTS contagens_deteccao (
  id              SERIAL PRIMARY KEY,
  camera_id       INTEGER REFERENCES ip_cameras(id) ON DELETE CASCADE,
  classe_id       INTEGER REFERENCES classes_yolo(id) ON DELETE CASCADE,
  quantidade      INTEGER DEFAULT 0,
  valor_total     DECIMAL(10,2) DEFAULT 0.00,
  sessao_id       VARCHAR(50),
  detectado_em    TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE contagens_deteccao IS 'Contagem de detecções YOLO por classe e sessão';
COMMENT ON COLUMN contagens_deteccao.valor_total IS 'Valor total calculado automaticamente';

CREATE INDEX idx_contagens_camera_sessao ON contagens_deteccao(camera_id, sessao_id);
CREATE INDEX idx_contagens_classe ON contagens_deteccao(classe_id);

-- ============================================
-- 003_create_versoes_modelo_table.sql
-- ============================================

CREATE TABLE IF NOT EXISTS versoes_modelo (
  id              SERIAL PRIMARY KEY,
  versao          VARCHAR(20) NOT NULL UNIQUE,
  classes_json    JSONB NOT NULL,
  epochs          INTEGER,
  map50           DECIMAL(5,4),
  arquivo_weights VARCHAR(255),
  ativo           BOOLEAN DEFAULT false,
  treinado_em     TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE versoes_modelo IS 'Histórico de versões do modelo YOLO treinado';
COMMENT ON COLUMN versoes_modelo.map50 IS 'Precisão mAP@50 do modelo treinado';

-- ============================================
-- 004_create_imagens_treinamento_table.sql
-- ============================================

CREATE TABLE IF NOT EXISTS imagens_treinamento (
  id              SERIAL PRIMARY KEY,
  classe_id       INTEGER REFERENCES classes_yolo(id) ON DELETE CASCADE,
  caminho         VARCHAR(500) NOT NULL,
  anotacao_yolo   TEXT,
  validada        BOOLEAN DEFAULT false,
  conjunto        VARCHAR(10) DEFAULT 'train',
  criado_em       TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE imagens_treinamento IS 'Imagens para treinamento do modelo YOLO';
COMMENT ON COLUMN imagens_treinamento.anotacao_yolo IS 'Anotação no formato YOLO: class_index x_center y_center width height';
COMMENT ON COLUMN imagens_treinamento.conjunto IS 'train, val ou test';

CREATE INDEX idx_imagens_classe ON imagens_treinamento(classe_id);
CREATE INDEX idx_imagens_validadas ON imagens_treinamento(validada) WHERE validada = true;
