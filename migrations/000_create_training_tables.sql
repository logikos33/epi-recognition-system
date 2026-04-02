-- Migration 000: Create training_videos and training_frames tables
-- These tables are referenced by migrations 004, 005, 005b, 006
-- but were never created in any previous migration

CREATE TABLE IF NOT EXISTS training_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID,
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500),
    original_path VARCHAR(500),
    duration_seconds FLOAT,
    frame_count INTEGER DEFAULT 0,
    fps FLOAT,
    uploaded_at TIMESTAMP DEFAULT NOW(),

    -- Processing columns (from migration 004)
    selected_start INTEGER,
    selected_end INTEGER,
    total_chunks INTEGER DEFAULT 0,
    processed_chunks INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'uploaded',

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_videos_user_id ON training_videos(user_id);
CREATE INDEX IF NOT EXISTS idx_training_videos_project_id ON training_videos(project_id);
CREATE INDEX IF NOT EXISTS idx_training_videos_status ON training_videos(status);

COMMENT ON TABLE training_videos IS 'Videos uploaded for YOLO model training';
COMMENT ON COLUMN training_videos.selected_start IS 'User-selected start second for videos > 10min (trimming)';
COMMENT ON COLUMN training_videos.selected_end IS 'User-selected end second for videos > 10min (trimming)';
COMMENT ON COLUMN training_videos.total_chunks IS 'Total number of 1-minute chunks to process';
COMMENT ON COLUMN training_videos.processed_chunks IS 'Number of chunks already processed (for progress tracking)';
COMMENT ON COLUMN training_videos.status IS 'Processing state: uploaded, extracting, completed, failed';
COMMENT ON COLUMN training_videos.original_path IS 'File system path to stored video file';

CREATE TABLE IF NOT EXISTS training_frames (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES training_videos(id) ON DELETE CASCADE,
    frame_number INTEGER NOT NULL,
    filepath VARCHAR(500),
    timestamp FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_frames_video_id ON training_frames(video_id);
CREATE INDEX IF NOT EXISTS idx_training_frames_frame_number ON training_frames(video_id, frame_number);

COMMENT ON TABLE training_frames IS 'Individual frames extracted from training videos';
COMMENT ON COLUMN training_frames.timestamp IS 'Timestamp in seconds from video start';
