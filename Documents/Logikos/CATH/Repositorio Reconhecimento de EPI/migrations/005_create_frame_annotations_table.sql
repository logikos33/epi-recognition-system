-- ============================================
-- Create frame_annotations Table
-- ============================================
-- Stores YOLO format bounding box annotations for each frame
-- Supports both manual annotations and AI-assisted annotations
-- NOTE: Foreign keys removed to avoid dependency on missing tables

CREATE TABLE frame_annotations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  frame_id UUID NOT NULL,
  class_id INTEGER NOT NULL,
  bbox_x NUMERIC(5, 4) NOT NULL, -- Normalized center X (0-1)
  bbox_y NUMERIC(5, 4) NOT NULL, -- Normalized center Y (0-1)
  bbox_width NUMERIC(5, 4) NOT NULL, -- Normalized width (0-1)
  bbox_height NUMERIC(5, 4) NOT NULL, -- Normalized height (0-1)
  confidence NUMERIC(3, 2), -- YOLO confidence (0-1), NULL for manual
  created_by VARCHAR(50) DEFAULT 'manual', -- 'manual' or 'ai_assisted'
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for query performance
CREATE INDEX idx_frame_annotations_frame_id ON frame_annotations(frame_id);
CREATE INDEX idx_frame_annotations_class_id ON frame_annotations(class_id);

-- Comments for documentation
COMMENT ON TABLE frame_annotations IS 'Stores YOLO format bounding box annotations for training frames';
COMMENT ON COLUMN frame_annotations.frame_id IS 'Reference to the frame being annotated (UUID, no FK constraint)';
COMMENT ON COLUMN frame_annotations.class_id IS 'Reference to the YOLO class ID (integer, no FK constraint)';
COMMENT ON COLUMN frame_annotations.bbox_x IS 'Normalized center X coordinate (0-1) in YOLO format';
COMMENT ON COLUMN frame_annotations.bbox_y IS 'Normalized center Y coordinate (0-1) in YOLO format';
COMMENT ON COLUMN frame_annotations.bbox_width IS 'Normalized width (0-1) in YOLO format';
COMMENT ON COLUMN frame_annotations.bbox_height IS 'Normalized height (0-1) in YOLO format';
COMMENT ON COLUMN frame_annotations.confidence IS 'YOLO detection confidence (0-1), NULL for manually created annotations';
COMMENT ON COLUMN frame_annotations.created_by IS 'Source of annotation: "manual" or "ai_assisted"';
