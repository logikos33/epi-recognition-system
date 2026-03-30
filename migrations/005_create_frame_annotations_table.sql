-- Tabela frame_annotations com foreign key correta para training_frames
CREATE TABLE IF NOT EXISTS frame_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    frame_id UUID NOT NULL,
    class_id INTEGER NOT NULL,
    bbox_x FLOAT NOT NULL,
    bbox_y FLOAT NOT NULL,
    bbox_width FLOAT NOT NULL,
    bbox_height FLOAT NOT NULL,
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_frame_annotations_frame
        FOREIGN KEY (frame_id)
        REFERENCES training_frames(id)
        ON DELETE CASCADE,
    
    CONSTRAINT fk_frame_annotations_user
        FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_frame_annotations_frame_id ON frame_annotations(frame_id);
CREATE INDEX IF NOT EXISTS idx_frame_annotations_class_id ON frame_annotations(class_id);
CREATE INDEX IF NOT EXISTS idx_frame_annotations_created_by ON frame_annotations(created_by);

-- Comentários
COMMENT ON TABLE frame_annotations IS 'Anotações de bounding boxes em frames de treinamento';
COMMENT ON COLUMN frame_annotations.bbox_x IS 'Coordenada X normalizada (0-1) do centro da box';
COMMENT ON COLUMN frame_annotations.bbox_y IS 'Coordenada Y normalizada (0-1) do centro da box';
COMMENT ON COLUMN frame_annotations.bbox_width IS 'Largura normalizada (0-1) da box';
COMMENT ON COLUMN frame_annotations.bbox_height IS 'Altura normalizada (0-1) da box';
