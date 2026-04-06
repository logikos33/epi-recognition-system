-- Training videos and extracted frames
CREATE TABLE IF NOT EXISTS training_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    storage_key TEXT,
    status TEXT NOT NULL DEFAULT 'uploaded',
    frame_count INTEGER DEFAULT 0,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training_frames (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES training_videos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    frame_number INTEGER NOT NULL,
    storage_key TEXT,
    is_annotated BOOLEAN DEFAULT FALSE,
    quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
