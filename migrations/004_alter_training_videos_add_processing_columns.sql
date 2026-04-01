-- ============================================
-- Add Video Processing Columns to training_videos
-- ============================================
-- This migration adds columns required for the video processing workflow:
-- - selected_start, selected_end: For trimming videos > 10min
-- - total_chunks, processed_chunks: For progress tracking during extraction
-- - status: For state management (uploaded, extracting, completed, failed)
-- - original_path: Path to stored video file

ALTER TABLE training_videos
  ADD COLUMN IF NOT EXISTS selected_start INTEGER,
  ADD COLUMN IF NOT EXISTS selected_end INTEGER,
  ADD COLUMN IF NOT EXISTS total_chunks INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS processed_chunks INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'uploaded',
  ADD COLUMN IF NOT EXISTS original_path VARCHAR(500);

-- Add comments for documentation
COMMENT ON COLUMN training_videos.selected_start IS 'User-selected start second for videos > 10min (trimming)';
COMMENT ON COLUMN training_videos.selected_end IS 'User-selected end second for videos > 10min (trimming)';
COMMENT ON COLUMN training_videos.total_chunks IS 'Total number of 1-minute chunks to process';
COMMENT ON COLUMN training_videos.processed_chunks IS 'Number of chunks already processed (for progress tracking)';
COMMENT ON COLUMN training_videos.status IS 'Processing state: uploaded, extracting, completed, failed';
COMMENT ON COLUMN training_videos.original_path IS 'File system path to stored video file';
