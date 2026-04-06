-- ============================================
-- Create classes_yolo Table
-- ============================================
-- Stores YOLO class definitions for object detection
-- This table is required for the annotation system

CREATE TABLE IF NOT EXISTS classes_yolo (
  id SERIAL PRIMARY KEY,
  nome VARCHAR(100) NOT NULL UNIQUE,
  cor_hex VARCHAR(7) NOT NULL, -- Hex color for bounding boxes (e.g., #FF0000)
  class_index INTEGER NOT NULL, -- Numeric index for YOLO model
  ativo BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Index for performance
CREATE INDEX idx_classes_yolo_nome ON classes_yolo(nome);
CREATE INDEX idx_classes_yolo_ativo ON classes_yolo(ativo);

-- Comments for documentation
COMMENT ON TABLE classes_yolo IS 'YOLO object detection classes (e.g., "EPI Capacete", "Luva")';
COMMENT ON COLUMN classes_yolo.nome IS 'Human-readable class name';
COMMENT ON COLUMN classes_yolo.cor_hex IS 'Hex color for visualization (e.g., #FF0000 for red)';
COMMENT ON COLUMN classes_yolo.class_index IS 'Numeric ID for YOLO model (0, 1, 2, ...)';
COMMENT ON COLUMN classes_yolo.ativo IS 'Whether this class is currently active for detection';
