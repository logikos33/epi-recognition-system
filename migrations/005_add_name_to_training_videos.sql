-- ============================================
-- Add name column to training_videos table
-- ============================================
-- This migration adds a human-readable name column for training videos

ALTER TABLE training_videos
  ADD COLUMN IF NOT EXISTS name VARCHAR(255);

COMMENT ON COLUMN training_videos.name IS 'Human-readable name for the training video';
