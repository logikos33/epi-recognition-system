-- ============================================
-- Create frames Table
-- ============================================
-- Stores extracted video frames for training annotation
-- Required for the annotation workflow

CREATE TABLE IF NOT EXISTS frames (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL,
  frame_number INTEGER NOT NULL,
  frame_path VARCHAR(500), -- File path to extracted frame image
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for query performance
CREATE INDEX idx_frames_video_id ON frames(video_id);
CREATE INDEX idx_frames_frame_number ON frames(frame_number);

-- Comments for documentation
COMMENT ON TABLE frames IS 'Extracted video frames for YOLO annotation';
COMMENT ON COLUMN frames.video_id IS 'Reference to training_videos table';
COMMENT ON COLUMN frames.frame_number IS 'Sequential frame number in the video';
COMMENT ON COLUMN frames.frame_path IS 'File system path to frame image';
