-- Supabase Schema for EPI Recognition System
-- Run this in your Supabase SQL Editor to create the required tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================== CAMERAS TABLE ====================
CREATE TABLE IF NOT EXISTS cameras (
    id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    rtsp_url TEXT,
    ip_address TEXT,
    rtsp_username TEXT,
    rtsp_password TEXT,  -- Note: Use row level security for production
    rtsp_port INTEGER DEFAULT 554,
    camera_brand TEXT DEFAULT 'generic',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_cameras_is_active ON cameras(is_active);
CREATE INDEX IF NOT EXISTS idx_cameras_brand ON cameras(camera_brand);

-- ==================== DETECTIONS TABLE ====================
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    camera_id INTEGER REFERENCES cameras(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    epis_detected JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence FLOAT DEFAULT 0.0,
    is_compliant BOOLEAN DEFAULT FALSE,
    person_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_detections_camera_id ON detections(camera_id);
CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detections_is_compliant ON detections(is_compliant);
CREATE INDEX IF NOT EXISTS idx_detections_camera_timestamp ON detections(camera_id, timestamp DESC);

-- ==================== WORKER STATUS TABLE ====================
CREATE TABLE IF NOT EXISTS worker_status (
    worker_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'idle',  -- active, idle, error, stale, stopped
    active_cameras INTEGER[] DEFAULT ARRAY[]::INTEGER[],
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_worker_status_status ON worker_status(status);
CREATE INDEX IF NOT EXISTS idx_worker_status_heartbeat ON worker_status(last_heartbeat DESC);

-- ==================== ROW LEVEL SECURITY (RLS) ====================
-- Enable RLS on all tables
ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_status ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your security requirements)

-- Cameras: Allow read access to all, write only to authenticated users
CREATE POLICY "Allow public read access on cameras"
    ON cameras FOR SELECT
    USING (true);

CREATE POLICY "Allow insert to authenticated users on cameras"
    ON cameras FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Allow update to authenticated users on cameras"
    ON cameras FOR UPDATE
    USING (auth.role() = 'authenticated');

CREATE POLICY "Allow delete to authenticated users on cameras"
    ON cameras FOR DELETE
    USING (auth.role() = 'authenticated');

-- Detections: Allow read access to all, write only to service role
CREATE POLICY "Allow public read access on detections"
    ON detections FOR SELECT
    USING (true);

CREATE POLICY "Allow insert to service role on detections"
    ON detections FOR INSERT
    WITH CHECK (auth.role() = 'service_role');

-- Worker Status: Allow all access (workers need full access)
CREATE POLICY "Allow all access on worker_status"
    ON worker_status FOR ALL
    USING (true)
    WITH CHECK (true);

-- ==================== FUNCTIONS AND TRIGGERS ====================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to auto-update updated_at
CREATE TRIGGER update_cameras_updated_at
    BEFORE UPDATE ON cameras
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_worker_status_updated_at
    BEFORE UPDATE ON worker_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==================== SAMPLE DATA (OPTIONAL) ====================
-- Uncomment to insert sample camera data

/*
INSERT INTO cameras (name, location, rtsp_url, ip_address, rtsp_username, rtsp_password, rtsp_port, camera_brand, is_active) VALUES
    ('Câmera Entrada Principal', 'Fábrica - Linha A', NULL, '189.0.0.100', 'admin', 'password123', 554, 'hikvision', true),
    ('Câmera Linha de Produção', 'Fábrica - Linha B', NULL, '189.0.0.101', 'admin', 'password123', 554, 'dahua', true),
    ('Câmera Depósito', 'Depósito Central', NULL, '189.0.0.102', 'admin', 'password123', 554, 'intelbras', true);
*/

-- ==================== VIEWS FOR COMMON QUERIES ====================

-- View for recent detections with camera info
CREATE OR REPLACE VIEW recent_detections_view AS
SELECT
    d.id,
    d.camera_id,
    c.name AS camera_name,
    c.location AS camera_location,
    d.timestamp,
    d.epis_detected,
    d.confidence,
    d.is_compliant,
    d.person_count
FROM detections d
JOIN cameras c ON d.camera_id = c.id
ORDER BY d.timestamp DESC
LIMIT 100;

-- View for compliance statistics by camera
CREATE OR REPLACE VIEW camera_compliance_stats AS
SELECT
    c.id AS camera_id,
    c.name AS camera_name,
    COUNT(d.id) AS total_detections,
    SUM(CASE WHEN d.is_compliant THEN 1 ELSE 0 END) AS compliant_detections,
    ROUND(
        CASE WHEN COUNT(d.id) > 0
            THEN SUM(CASE WHEN d.is_compliant THEN 1 ELSE 0 END)::FLOAT / COUNT(d.id) * 100
            ELSE 0
        END,
        2
    ) AS compliance_rate_percent
FROM cameras c
LEFT JOIN detections d ON c.id = d.camera_id
    AND d.timestamp > NOW() - INTERVAL '24 hours'
GROUP BY c.id, c.name
ORDER BY compliance_rate_percent DESC;

-- ==================== CLEANUP JOB ====================
-- Function to clean up old detections (optional - for data retention)
CREATE OR REPLACE FUNCTION cleanup_old_detections(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM detections
    WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comment out the line below to enable automatic cleanup
-- SELECT cron_schedule('cleanup-old-detections', '0 2 * * *', 'SELECT cleanup_old_detections(30)');

-- ==================== NOTES ====================
-- 1. Update RLS policies based on your authentication requirements
-- 2. Adjust retention periods in the cleanup function
-- 3. Add additional indexes based on your query patterns
-- 4. Consider adding materialized views for complex analytics
-- 5. For production, use Supabase Vault to store sensitive data like RTSP passwords
