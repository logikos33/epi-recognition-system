from sqlalchemy import create_engine, text
import os

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    sql = """
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
"""
    conn.execute(text(sql))
    conn.commit()
    print("✅ Migration executada - training_videos e training_frames criadas")
