-- IP Cameras table
CREATE TABLE IF NOT EXISTS ip_cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    manufacturer TEXT NOT NULL DEFAULT 'generic',
    ip TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 554,
    username TEXT,
    password_encrypted TEXT,
    rtsp_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
