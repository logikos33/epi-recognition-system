-- YOLO classes and frame annotations
CREATE TABLE IF NOT EXISTS yolo_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#00ff00',
    yolo_index INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS frame_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    frame_id UUID NOT NULL REFERENCES training_frames(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    class_id UUID REFERENCES yolo_classes(id),
    x_center FLOAT NOT NULL,
    y_center FLOAT NOT NULL,
    width FLOAT NOT NULL,
    height FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
