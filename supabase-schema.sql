-- EPI Recognition System - Supabase Database Schema
-- Execute this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. USERS TABLE (Custom users table)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    company_name VARCHAR(255),
    phone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    role VARCHAR(50) DEFAULT 'user', -- 'user' or 'admin'
    last_login TIMESTAMP WITH TIME ZONE
);

-- Index for faster email lookups
CREATE INDEX idx_users_email ON users(email);

-- ============================================
-- 2. CAMERAS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    description TEXT,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'maintenance'
    rtsp_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for user's cameras
CREATE INDEX idx_cameras_user_id ON cameras(user_id);

-- ============================================
-- 3. DETECTIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(id) ON DELETE SET NULL,
    image_url TEXT, -- URL to stored image
    objects_detected JSONB NOT NULL, -- Array of detected objects
    total_objects INTEGER DEFAULT 0,
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB -- Additional metadata
);

-- Indexes for common queries
CREATE INDEX idx_detections_user_id ON detections(user_id);
CREATE INDEX idx_detections_camera_id ON detections(camera_id);
CREATE INDEX idx_detections_created_at ON detections(created_at DESC);

-- ============================================
-- 4. ALERTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(id) ON DELETE SET NULL,
    detection_id UUID REFERENCES detections(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL, -- 'no_epi', 'no_helmet', 'no_vest', etc
    severity VARCHAR(50) DEFAULT 'warning', -- 'low', 'warning', 'critical'
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for alert queries
CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_is_read ON alerts(is_read);
CREATE INDEX idx_alerts_created_at ON alerts(created_at DESC);

-- ============================================
-- 5. SESSIONS TABLE (for JWT refresh tokens)
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    refresh_token VARCHAR(500),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Index for token lookups
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid()::text = id::text);

-- Cameras policy
CREATE POLICY "Users can view own cameras" ON cameras
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own cameras" ON cameras
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own cameras" ON cameras
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own cameras" ON cameras
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- Detections policy
CREATE POLICY "Users can view own detections" ON detections
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own detections" ON detections
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

-- Alerts policy
CREATE POLICY "Users can view own alerts" ON alerts
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own alerts" ON alerts
    FOR UPDATE USING (auth.uid()::text = user_id::text);

-- Sessions policy
CREATE POLICY "Users can view own sessions" ON sessions
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- ============================================
-- FUNCTIONS AND TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cameras_updated_at BEFORE UPDATE ON cameras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================

-- Insert a test user (password: 'test123' - hash will be generated)
-- Uncomment for testing:
-- INSERT INTO users (email, password_hash, full_name, company_name)
-- VALUES ('test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEmc7i', 'Test User', 'Test Company');

-- ============================================
-- USEFUL QUERIES
-- ============================================

-- Get all detections for a user in last 7 days
-- SELECT * FROM detections
-- WHERE user_id = 'user-uuid'
-- AND created_at >= NOW() - INTERVAL '7 days'
-- ORDER BY created_at DESC;

-- Get detection statistics
-- SELECT
--     DATE(created_at) as date,
--     COUNT(*) as total_detections,
--     SUM(total_objects) as total_objects
-- FROM detections
-- WHERE user_id = 'user-uuid'
-- GROUP BY DATE(created_at)
-- ORDER BY date DESC;

-- Get unread alerts
-- SELECT * FROM alerts
-- WHERE user_id = 'user-uuid'
-- AND is_read = FALSE
-- ORDER BY created_at DESC;
