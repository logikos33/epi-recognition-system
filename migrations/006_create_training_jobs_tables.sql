-- ============================================
-- Training Jobs and Trained Models Tables
-- ============================================
-- This migration creates tables for managing YOLO training jobs and trained models

-- Training Jobs Table
-- Stores metadata about training runs
CREATE TABLE IF NOT EXISTS training_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Job configuration
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed, stopped
    preset VARCHAR(20) NOT NULL,  -- fast, balanced, quality
    model_size VARCHAR(10) NOT NULL,  -- n, s, m
    epochs INTEGER NOT NULL,

    -- Paths
    dataset_yaml_path VARCHAR(500),
    model_output_path VARCHAR(500),

    -- Progress tracking
    progress INTEGER DEFAULT 0,  -- 0-100
    current_epoch INTEGER DEFAULT 0,

    -- Metrics (JSONB for flexibility)
    metrics JSONB,

    -- Error tracking
    error_message TEXT,

    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE training_jobs IS 'YOLO training jobs for custom model training';
COMMENT ON COLUMN training_jobs.status IS 'Job status: pending, running, completed, failed, stopped';
COMMENT ON COLUMN training_jobs.preset IS 'Training preset: fast (yolov8n, 50ep), balanced (yolov8s, 100ep), quality (yolov8m, 150ep)';
COMMENT ON COLUMN training_jobs.model_size IS 'YOLO model size: n (nano), s (small), m (medium)';
COMMENT ON COLUMN training_jobs.metrics IS 'Training metrics: mAP50, mAP95, precision, recall, etc.';

-- Indexes for performance
CREATE INDEX idx_training_jobs_user_id ON training_jobs(user_id);
CREATE INDEX idx_training_jobs_status ON training_jobs(status);
CREATE INDEX idx_training_jobs_created_at ON training_jobs(created_at DESC);


-- Trained Models Table
-- Stores successfully trained models that can be activated
CREATE TABLE IF NOT EXISTS trained_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES training_jobs(id) ON DELETE SET NULL,

    -- Model information
    name VARCHAR(255) NOT NULL,
    model_path VARCHAR(500) NOT NULL,
    model_size VARCHAR(10) NOT NULL,  -- n, s, m

    -- Activation status (only one model per user can be active)
    is_active BOOLEAN DEFAULT FALSE,

    -- Performance metrics
    metrics JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE trained_models IS 'Trained YOLO models ready for deployment';
COMMENT ON COLUMN trained_models.is_active IS 'Only one model per user can be active at a time';

-- Indexes
CREATE INDEX idx_trained_models_user_id ON trained_models(user_id);
CREATE INDEX idx_trained_models_is_active ON trained_models(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_trained_models_job_id ON trained_models(job_id);

-- Unique constraint: Only one active model per user
CREATE UNIQUE INDEX idx_trained_models_user_active ON trained_models(user_id)
WHERE is_active = TRUE;
